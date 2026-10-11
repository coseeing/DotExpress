"""Shared helpers for the F-12 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses, unchanged, f9gui.py of F-9 and through it f8bgui.py, f8agui.py, f7gui.py, f5gui.py
and dx.py, docs.py, dicts.py of the 2026-10-09-03 Windows verification. Every item builds
its work folder before the start: packages with zipfile, config.json, dictionaries and
preprocessing.py as bytes. Message boxes are task dialogs, read through UIA
(f5gui.describe: title, main instruction, content, buttons, focus) and answered with a key.
Keys go only to a window of the app under test while it is in the foreground (safe_run.py
enforces it for every send_keys). The work folder is shown as <d>. Nothing here touches the
clipboard.
"""
import ctypes
import os
import re
import subprocess
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-10-07-f9-conversion-target-document", "auto"))
import f9gui as H  # noqa: E402  (puts the F-8b, F-8a, F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f9gui import A, B, D, F, G, dx  # noqa: E402

F9 = H
EXPORT_DIALOG = H.EXPORT_DIALOG
EXPORT_ALL_DIALOG = H.EXPORT_ALL_DIALOG
IMPORT_DIALOG = H.IMPORT_DIALOG
import dicts as X  # noqa: E402

SETTINGS = "DotExpress 設定"
IMPORT_ISSUES = "匯入問題"
WM_GETFONT = 0x0031
GW_OWNER = 4
HEADER = "text,braille,type\r\n"


class LOGFONTW(ctypes.Structure):
	_fields_ = [
		("lfHeight", wintypes.LONG),
		("lfWidth", wintypes.LONG),
		("lfEscapement", wintypes.LONG),
		("lfOrientation", wintypes.LONG),
		("lfWeight", wintypes.LONG),
		("lfItalic", wintypes.BYTE),
		("lfUnderline", wintypes.BYTE),
		("lfStrikeOut", wintypes.BYTE),
		("lfCharSet", wintypes.BYTE),
		("lfOutPrecision", wintypes.BYTE),
		("lfClipPrecision", wintypes.BYTE),
		("lfQuality", wintypes.BYTE),
		("lfPitchAndFamily", wintypes.BYTE),
		("lfFaceName", wintypes.WCHAR * 32),
	]


TMP_NAME = re.compile(r"(\.[\w.]+?\.(?:dep|csv|brl|html|json|bak)\.)[A-Za-z0-9_]{8,16}(\.tmp)")


def masked(d, value):
	"""``value`` as text (f9gui.masked), the random part of any temporary file name as <rnd>."""
	return TMP_NAME.sub(r"\1<rnd>\2", H.masked(d, value))


def write(path, data):
	return A.write(path, data)


def dictionary(d, name, data):
	"""dictionary\\<name>.csv with ``data`` (bytes)."""
	return A.write(os.path.join(d, "dictionary", f"{name}.csv"), data)


def config(d, data):
	"""config.json with ``data`` (bytes)."""
	return A.write(os.path.join(d, "config.json"), data)


def preprocessing(d, source):
	"""dictionary\\preprocessing.py (the text processing script) with ``source``."""
	return A.write(os.path.join(d, "dictionary", "preprocessing.py"), source.encode("utf-8"))


def prepare(exe, d):
	"""A new work folder with workspace\\ and the exe (f8agui.prepare)."""
	return A.prepare(exe, d)


def start(d):
	"""Start the app; Keep for the invalid-files dialog; each startup box read and answered."""
	return B.start(d)


def box(app, d, timeout=10, key="enter"):
	"""The next message box, answered with ``key`` (masked), or None if none opens in time.

	``owner`` is the title of the window that owns the box (the main window is shown as
	"<main>"). How often the key was pressed is left out.
	"""
	import win32gui

	found = G.wait_box(app, timeout)
	if found is None:
		return None
	owner_handle = win32gui.GetWindow(found.handle, GW_OWNER)
	described = F.describe(found)
	owner = win32gui.GetWindowText(owner_handle) if owner_handle else None
	described["owner"] = "<main>" if owner and owner.endswith("DotExpress") else owner
	F.answer(found, key)
	return masked(d, described)


def boxes(app, d, timeout=5):
	"""Every box that opens now, one after the other (each answered with Enter)."""
	shown = []
	while True:
		found = box(app, d, timeout)
		if found is None:
			return shown
		shown.append(found)
		timeout = 3


def import_issues(app, w, timeout=10):
	"""The lines of the Import Issues dialog (closed with its OK), or None if it does not open."""
	issues = A.maybe_window(app, w, IMPORT_ISSUES, timeout=timeout)
	if issues is None:
		return None
	lines = issues.child_window(class_name="ListBox").wrapper_object().item_texts()
	X.btn(issues, "確定", "OK").click()
	time.sleep(1)
	return lines


def editor_font_height(w):
	"""lfHeight of the source editor's font (WM_GETFONT): it changes with the font size."""
	gdi32 = ctypes.WinDLL("gdi32")
	editor = w.children(class_name="Edit")[0]
	font = editor.send_message(WM_GETFONT, 0, 0)
	logfont = LOGFONTW()
	gdi32.GetObjectW(wintypes.HANDLE(font), ctypes.sizeof(LOGFONTW), ctypes.byref(logfont))
	return logfont.lfHeight


def settings(app, w):
	"""Translation > Settings: the settings dialog (modeless)."""
	G.menu(w, "#1->#4")
	return G.window_titled(app, w, SETTINGS)


def width_control(dialog):
	"""The conversion width field of the settings dialog's first page (its only Edit)."""
	return [c for c in dialog.wrapper_object().descendants() if c.class_name() == "Edit" and c.is_visible()][0]


def press(dialog, *labels, wait=1.5):
	"""Press the button ``labels`` with BM_CLICK, so that no key is needed."""
	X.btn(dialog, *labels).click()
	time.sleep(wait)


def lock(path, share="none"):
	"""Hold ``path`` open in another process with ``share`` (F-8a's lockshare.py)."""
	return A.lock(path, share=share)


def unlock(process):
	A.unlock(process)


def deny_read(path):
	"""Add an access-control entry that denies the current user reading ``path`` (icacls)."""
	user = os.environ["USERNAME"]
	done = subprocess.run(["icacls", path, "/deny", f"{user}:(R)"], capture_output=True, text=True)
	return done.returncode


def allow_read(path):
	user = os.environ["USERNAME"]
	return subprocess.run(["icacls", path, "/remove:d", user], capture_output=True, text=True).returncode


def finish(app, w, d):
	print("close:", masked(d, D.close(app, w)))
	dx.kill_under(d)


def select_config(d, name=None, extra=None):
	"""config.json selecting dictionary ``name`` (UTF-8 JSON bytes), with ``extra`` merged in."""
	import json

	conversion = {"selected_dictionary": name} if name else {}
	data = {"conversion": conversion}
	data.update(extra or {})
	return A.write(os.path.join(d, "config.json"), json.dumps(data).encode("utf-8"))


def set_source(w, text):
	"""Put ``text`` in the source editor (set_edit_text: no clipboard)."""
	w.children(class_name="Edit")[0].set_edit_text(text)
	time.sleep(0.5)


def convert_menu(w):
	"""Translation > Convert (a manual conversion of the open document)."""
	G.menu(w, "#1->#0", wait=0.5)


def braille_text(w):
	return w.children(class_name="Edit")[1].window_text()


def restart(app, w, d):
	"""Close the app (answering what it shows), end anything under <d>, start again."""
	print("   close:", masked(d, D.close(app, w)))
	dx.kill_under(d)
	return start(d)


def settle(app, w, d, handlers, seconds=30):
	"""Answer, for ``seconds``, every message box and the invalid-files dialog that opens.

	Returns the list of what was shown, in order. A message box is read and answered with
	Enter; the invalid-files dialog is read and answered with Keep.
	"""
	shown = []
	end = time.time() + seconds
	idle = 0
	while time.time() < end and idle < 3:
		found = box(app, d, timeout=1.5, key=handlers.get("key", "enter"))
		if found is not None:
			shown.append(found)
			idle = 0
			continue
		invalid = A.maybe_window(app, w, A.INVALID_FILES, timeout=1)
		if invalid is not None:
			import dicts

			shown.append(("invalid", invalid.child_window(class_name="ListBox").wrapper_object().item_texts()))
			dicts.btn(invalid, A.KEEP_INVALID).click()
			time.sleep(1)
			idle = 0
			continue
		idle += 1
	return shown


def close_app(app, w, d):
	"""Close the app (answering what it shows) and end anything under <d>."""
	print("   close:", masked(d, D.close(app, w)))
	dx.kill_under(d)
