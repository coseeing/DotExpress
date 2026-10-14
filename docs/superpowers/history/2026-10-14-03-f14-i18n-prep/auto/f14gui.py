"""Shared helpers for the F-14 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses, unchanged, f12gui.py of F-12 (and through it f9gui.py, f8bgui.py, f8agui.py,
f7gui.py, f5gui.py and dx.py, docs.py, dicts.py of the 2026-10-09-03 Windows verification)
and f11gui.py of F-11 (the dictionary editor). The builds under test (N-f14, N-f12b) start
as before F-13, so the old start helpers apply. Added here: the readers of F-14's items:
the first lines of an exported HTML file, the About box, the settings dialog through UIA
(title, category list, each panel's accessible description), the dictionary editor's Type
column and the entry dialog's Type choice, and the Dual View page. Translation > Dual View
opens the page in a browser (gui.on_open_dual_view -> _open_dual_view_in_browser): a run
first puts a stand-in "browser" (a copy of where.exe named chrome.exe, under the work
folder) first on PATH, so no real browser starts, and reads the page the app wrote to
<d>\\dual_view before the app ends (it removes that folder's files at exit).
Work folders are built by script; keys go only to a window of the app under test while it
is in the foreground (safe_run.py). The work folder is shown as <d>. Nothing here touches
the clipboard.
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HISTORY, "2026-10-11-02-f12-localization-cleanup", "auto"))
import f12gui as H12  # noqa: E402  (puts the F-9, F-8b, F-8a, F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f12gui import A, D, F, F9, G, X, dx  # noqa: E402

sys.path.insert(0, os.path.join(HISTORY, "2026-10-11-01-f11-dictionary-editor-ux", "auto"))
import f11gui as H11  # noqa: E402

SETTINGS = H12.SETTINGS
EMPTY_PAGE = "此文件沒有可顯示的轉換資料。"
LEGACY_DESCRIPTION = 30094  # UIA_LegacyIAccessibleDescriptionPropertyId
LANG = re.compile(r'<html lang="([^"]*)">')
# The work folder of the item; safe_run.py sets it. Keys go only to windows of processes under it.
FOLDER = None
# The stand-in browser folder that fake_browser put first on PATH; dual_view_page refuses
# to open the Dual View without it, so no helper here can start a real browser (F-14 review M-1).
STAND_IN = None


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


def masked(d, value):
	return H12.masked(d, value)


def html_file(path):
	"""The first two lines of an exported HTML file, its lang, its cells and whether it shows the empty page."""
	if not os.path.exists(path):
		return "missing"
	with open(path, "rb") as stream:
		data = stream.read()
	text = data.decode("utf-8")
	lines = text.splitlines()
	found = LANG.search(text)
	return {
		"first lines": lines[:2],
		"lang": found.group(1) if found else None,
		"cells": text.count('class="source"'),
		"empty page (zh)": EMPTY_PAGE in text,
		"crlf": b"\r\n" in data,
	}


def about(app, w, d):
	"""Help > About: the box (title, main instruction, content, owner), answered with Enter."""
	G.menu(w, "#2->#1", wait=1)
	return H12.box(app, d, timeout=10)


def uia(window):
	from pywinauto import Desktop

	return Desktop(backend="uia").window(handle=window.handle)


def legacy_description(element):
	"""LegacyIAccessible.Description of a UIA element (what the MSAA description gives a screen reader)."""
	try:
		return element.element_info.element.GetCurrentPropertyValue(LEGACY_DESCRIPTION)
	except Exception as error:
		return f"<unreadable: {type(error).__name__}>"


def settings_view(dialog):
	"""The settings dialog as UIA shows it: title, category items, the shown panel and its description.

	The panel is the visible Pane named after a category (SettingsPanel.SetName)."""
	window = uia(dialog)
	categories = [item.window_text() for item in window.descendants(control_type="ListItem")]
	panels = [
		element
		for element in window.descendants(control_type="Pane")
		if element.window_text() in categories and element.is_visible()
	]
	return {
		"title": dialog.window_text(),
		"categories": categories,
		"panels": [(panel.window_text(), legacy_description(panel)) for panel in panels],
	}


def ctrl_tab(dialog):
	"""Ctrl+Tab in the settings dialog (the next category), only while it is in the foreground."""
	H11.keys(dialog, "^{TAB}", wait=1.0)


def editor_types(app, w, name):
	"""Dictionary Management > Edit ``name``: the rows, then Add: the Type choice items; both closed with Cancel."""
	editor = H11.editor(app, w, name)
	rows = X.editor_rows(editor)
	H11.press_button(editor, "新增")
	entry = H11.entry_dialog(app, w, H11.ADD_ENTRY)
	combo = [c for c in entry.wrapper_object().descendants() if c.class_name() == "ComboBox"][0]
	choices = combo.item_texts()
	selected = combo.selected_text()
	H11.press_button(entry, "取消")
	H11.press_button(editor, "取消")
	left = H11.next_box(app, "enter", timeout=3)
	H11.close_manager(app, w)
	return {"rows": rows, "choice items": choices, "choice selected": selected, "box after Cancel": left}


def fake_browser(d):
	"""Put a stand-in chrome.exe (a copy of where.exe, which only prints an error for the
	browser's arguments and ends) under <d>\\fakebrowser and that folder first on PATH, so
	that the app started from this process finds it before any real browser
	(dual_view.browser.find_browser_executable tries chrome first, through PATH first)."""
	import shutil

	global STAND_IN
	folder = os.path.join(d, "fakebrowser")
	os.makedirs(folder, exist_ok=True)
	shutil.copy(os.path.join(os.environ["SystemRoot"], "System32", "where.exe"), os.path.join(folder, "chrome.exe"))
	os.environ["PATH"] = folder + os.pathsep + os.environ["PATH"]
	STAND_IN = folder
	return folder


def dual_view_page(app, w, d, timeout=20):
	"""Translation > Dual View with the stand-in browser: the page the app wrote to
	<d>\\dual_view (html_file), and the boxes that opened. Refuses (RuntimeError) unless
	fake_browser put its stand-in first on PATH: Translation > Dual View would otherwise
	start the user's real browser."""
	if STAND_IN is None or os.environ["PATH"].split(os.pathsep)[0] != STAND_IN:
		raise RuntimeError("no stand-in browser first on PATH; call fake_browser(d) before the app starts")
	folder = os.path.join(d, "dual_view")
	before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
	G.menu(w, "#1->#1", wait=1)
	end = time.time() + timeout
	new = []
	while time.time() < end and not new:
		time.sleep(0.5)
		new = sorted(set(os.listdir(folder)) - before) if os.path.isdir(folder) else []
	time.sleep(0.5)
	pages = {name[:10] + "<token>.html": html_file(os.path.join(folder, name)) for name in new}
	return {"pages": pages, "boxes": H12.boxes(app, d, timeout=2)}


def config_log(d):
	"""The messages of the ERROR lines of log\\config.log and whether its traceback holds WinError 5."""
	path = os.path.join(d, "log", "config.log")
	if not os.path.exists(path):
		return "missing"
	with open(path, encoding="utf-8", errors="replace") as stream:
		text = stream.read()
	errors = [line.split("[ERROR] ", 1)[1] for line in text.splitlines() if "[ERROR] " in line]
	return {"error lines": [masked(d, line) for line in errors], "WinError 5 in the traceback": "WinError 5" in text}


def finish(app, w, d):
	H12.finish(app, w, d)
