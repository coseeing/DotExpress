"""Shared helpers for the F-9 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses f8bgui.py of F-8b (and through it f8agui.py, f7gui.py, f5gui.py and the helpers
of the 2026-10-09-03 Windows verification) unchanged. A conversion that runs for several
seconds comes from a long source text, LONG_REPEAT copies of UNIT (520,000 characters)
written into a package by script; the plan's dry run measured about 15 s for one
conversion of it. Keys go to the main window only while it is the foreground window
(``keys`` checks that first and stops the item otherwise, so no key reaches another
program). Output shows long texts by their length and first characters, the work folder
as <d> and the random part of a temporary file name as <rnd>. Nothing here touches the
clipboard.
"""
import os
import re
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
F8B = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-06-f8b-recovery-and-nul", "auto"))
sys.path.insert(0, F8B)
import f8bgui as B  # noqa: E402  (puts the F-8a, F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f8bgui import A, D, F, G, dx  # noqa: E402

UNIT = "這是一段測試用的中文文字，DotExpress converts it to braille. 第二句還有數字 123 和符號。\n"
LONG_REPEAT = 8000
EXPORT_DIALOG = "匯出文件"
EXPORT_ALL_DIALOG = "匯出全部文件"
IMPORT_DIALOG = "匯入文件"
RANDOM_TMP = re.compile(r"(\.[\w.]+?\.dep\.)[A-Za-z0-9_]{8,16}(\.tmp)")


def long_text():
	return UNIT * LONG_REPEAT


def pending(d, name, text):
	"""workspace\\<name>.dep holding ``text`` with no braille yet (the app's pending marker)."""
	path = A.package(d, name, text, "")
	with zipfile.ZipFile(path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"{name}.meta.json", '{"braille_pending": true}')
	return path


def short(text):
	"""``repr`` of a short text; a long one as its length and first characters."""
	if text is None or len(text) <= 24:
		return repr(text)
	return f"<{len(text)} chars {text[:6]!r}...>"


def masked(d, value):
	"""``value`` as text, with the work folder as <d> and random temporary names as <rnd>."""
	text = B.show(value) if not isinstance(value, str) else value
	# A path inside an error message is a repr already, so it can be escaped twice.
	for form in (d.replace("\\", "\\" * 4), d.replace("\\", "\\" * 2), d):
		text = text.replace(form, "<d>")
	return RANDOM_TMP.sub(r"\1<rnd>\2", text)


def package(d, name):
	"""What workspace\\<name>.dep holds: its text and braille, shortened, and whether it is pending."""
	path = os.path.join(d, "workspace", f"{name}.dep")
	if not os.path.exists(path):
		return "missing"
	with zipfile.ZipFile(path) as archive:
		names = archive.namelist()
		text = archive.read(f"{name}.txt").decode("utf-8")
		braille = archive.read(f"{name}.brl").decode("utf-8")
	return f"text {short(text)} braille {short(braille)}{' (pending)' if f'{name}.meta.json' in names else ''}"


def editors(w):
	"""The window title and what the source and Braille Result editors show (WM_GETTEXT)."""
	source, braille = (control.window_text() for control in w.children(class_name="Edit")[:2])
	return f"{w.window_text()!r} source {short(source)} braille {short(braille)}"


def keys(w, sequence):
	"""Send ``sequence`` once the main window is the foreground window; raise if it never is."""
	import win32gui
	from pywinauto.keyboard import send_keys

	for _attempt in range(10):
		if win32gui.GetForegroundWindow() == w.handle:
			send_keys(sequence)
			time.sleep(0.5)
			return
		w.set_focus()
		time.sleep(0.3)
	raise RuntimeError(f"the main window is not in the foreground; {sequence!r} was not sent")


def convert(w):
	"""Ctrl+Enter in the source editor: a manual conversion of the open document."""
	w.children(class_name="Edit")[0].set_focus()
	keys(w, "^{ENTER}")


def box_open(app):
	"""Whether a message box is open now (a conversion that ended too soon shows its box).

	False if the windows cannot be read, as when the app has just ended.
	"""
	try:
		return bool(G.task_dialogs(app))
	except Exception:
		return False


def box(app, d, timeout):
	"""The next message box, answered with Enter (masked), or None if none opens within ``timeout`` s.

	How often Enter was pressed (f5gui.answer presses again if a key was lost) is left out:
	it depends on the foreground, not on the app.
	"""
	shown = G.answer_box(app, "enter", timeout=timeout)
	if shown is None:
		return None
	shown.pop("presses", None)
	return masked(d, shown)


def export_path(app, w, title, path):
	"""Fill the Save or folder dialog ``title`` with ``path`` and press its button (f7gui)."""
	G.path_dialog(app, w, title, path)


def html_summary(path):
	"""Whether an exported HTML file shows converted segments or the "No conversion data" page."""
	if not os.path.exists(path):
		return "missing"
	with open(path, encoding="utf-8") as stream:
		html = stream.read()
	segments = html.count('class="source"')
	return f"segments {segments} no-data {'No conversion data' in html}"


def written(folder):
	"""{file: its text, shortened} of an export folder."""
	result = {}
	for name in sorted(os.listdir(folder)):
		with open(os.path.join(folder, name), encoding="utf-8") as stream:
			result[name] = short(stream.read())
	return result


def call_state(sender):
	"""How a SessionMessage (f7gui) ended: its result, and whether it returned within 2 s."""
	if sender.returned_after is None:
		return "not returned"
	return {"ok": sender.ok, "result": sender.result, "within_2_s": sender.returned_after < 2}


def process_handle(pid):
	"""A handle to process ``pid`` that keeps its exit code readable after it ends."""
	import win32api

	# PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
	return win32api.OpenProcess(0x1000 | 0x00100000, False, pid)


def ended(handle):
	"""None while the process runs; once it has ended, whether its exit code is nonzero."""
	import win32process

	code = win32process.GetExitCodeProcess(handle)
	return None if code == 259 else code != 0


def next_box(app, d, process, timeout):
	"""The next message box (as ``box`` gives it), "ended" if the app ends first, or None
	if neither happens within ``timeout`` s. ``process`` comes from ``process_handle``."""
	end = time.time() + timeout
	while time.time() < end:
		if ended(process) is not None:
			return "ended"
		if box_open(app):
			return box(app, d, timeout=5)
		time.sleep(0.5)
	return None


def finish(app, w, d):
	print("close:", masked(d, D.close(app, w)))
	dx.kill_under(d)
