"""Shared helpers for the F-8b GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses f8agui.py of F-8a (and through it f7gui.py, f5gui.py and the helpers of the
2026-10-09-03 Windows verification) unchanged. Startup can show message boxes before
the main window appears (the recovery box, the U+0000 box of the first document) as
well as the invalid-files dialog: ``start`` answers each one and returns what it showed.
Work folders are built by script: packages are written with zipfile, and U+0000 reaches
the app only through files. Nothing here touches the clipboard. Output shows U+FFFD as
<U+FFFD>. The review fix (F-8b2 build) added ``gui_log``, ``REPLACED_CONTENT`` and
``replaced_box_ok``.
"""
import os
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
F8A = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-10-05-f8a-data-safety-cleanup", "auto"))
sys.path.insert(0, F8A)
import f8agui as A  # noqa: E402  (puts the F-7, F-5 and 2026-10-09-03 auto folders on sys.path)
from f8agui import D, F, G, X, dx  # noqa: E402

IMPORT_DIALOG = "匯入文件"
REPLACEMENT = chr(0xFFFD)
REPLACED_TITLE = "已取代字元"
# The second paragraph of the U+0000 box since the review fix (M-5: 轉換前, before 轉譯前).
REPLACED_CONTENT = "轉換前請刪除或修改這些 <U+FFFD>，否則每一個都會在點字中變成一段跳脫碼。"


def show(value):
	"""``repr(value)`` with U+FFFD written as <U+FFFD>."""
	return repr(value).replace(REPLACEMENT, "<U+FFFD>")


def leftover(d, file_name, name, text, braille, age_s=0):
	"""workspace\\<file_name> holding a package of ``name`` (as a crash leaves it), ``age_s`` seconds old."""
	path = os.path.join(d, "workspace", file_name)
	with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(f"{name}.txt", text)
		archive.writestr(f"{name}.brl", braille)
	modified = time.time() - age_s
	os.utime(path, (modified, modified))
	return path


def replaced_box_ok(box):
	"""Whether ``box`` (an f5gui.describe dict) is the 已取代字元 box with the expected content."""
	return box.get("title") == REPLACED_TITLE and box.get("content", "").replace(REPLACEMENT, "<U+FFFD>") == REPLACED_CONTENT


def replaced_boxes_ok(boxes):
	"""``replaced_box_ok`` for each 已取代字元 box among ``boxes`` (dicts; other entries are skipped)."""
	return [replaced_box_ok(box) for box in boxes if isinstance(box, dict) and box.get("title") == REPLACED_TITLE]


def gui_log(d):
	"""The lines of log\\gui.log without their timestamps ([] if there is none)."""
	data = A.read(os.path.join(d, "log", "gui.log"))
	if data is None:
		return []
	return [line[24:] for line in data.decode("utf-8", "replace").splitlines() if line[:4].isdigit()]


def temporary_files(d):
	"""{name: sha256 prefix} of the .tmp files in workspace\\."""
	return {name: A.sha(os.path.join(d, "workspace", name)) for name in A.files(d) if name.endswith(".tmp")}


def members(d, name):
	"""(text, braille) of workspace\\<name>.dep as stored, or None if it is missing."""
	path = os.path.join(d, "workspace", f"{name}.dep")
	if not os.path.exists(path):
		return None
	with zipfile.ZipFile(path) as archive:
		return archive.read(f"{name}.txt").decode("utf-8"), archive.read(f"{name}.brl").decode("utf-8")


def start(d, timeout=40):
	"""Start <d>\\DotExpress.exe and answer what startup shows before the main window.

	The invalid-files dialog is answered with Keep; each message box is read through UIA
	(f5gui.describe) and answered with Enter. Returns (app, w, shown): ``shown`` lists in
	order ("invalid", <its list>) and the description of each box. If the main window
	does not appear, returns (None, None, shown + [how the start ended]).
	"""
	from pywinauto import Application, Desktop

	launcher = subprocess.Popen([os.path.join(d, "DotExpress.exe")], cwd=d)
	started = time.time()
	shown = []
	handled = set()
	while time.time() - started < timeout:
		for handle, title in A.top_windows(d):
			if handle in handled:
				continue
			if title.endswith("DotExpress"):
				app, w = dx.attach(d)
				return app, w, shown
			win = Application(backend="win32").connect(handle=handle).window(handle=handle)
			if title == A.INVALID_FILES:
				shown.append(("invalid", win.child_window(class_name="ListBox").wrapper_object().item_texts()))
				X.btn(win, A.KEEP_INVALID).click()
				handled.add(handle)
				time.sleep(1)
			elif G.is_task_dialog(win):
				box = Desktop(backend="uia").window(handle=handle)
				described = F.describe(box)
				described["presses"] = F.answer(box, "enter")
				shown.append(described)
				handled.add(handle)
		if launcher.poll() is not None and not A.processes(d):
			return None, None, shown + [f"no main window; exited with code {launcher.returncode}"]
		time.sleep(0.5)
	return None, None, shown + [f"no main window after {timeout} s: {A.top_windows(d)}"]


def box(app, timeout=3):
	"""The next message box (answered with Enter), or None if none opens within ``timeout`` s."""
	return G.answer_box(app, "enter", timeout=timeout)


def switch(app, w, back=False):
	"""Ctrl+Tab (Ctrl+Shift+Tab if ``back``): (the box it showed, the title)."""
	from pywinauto.keyboard import send_keys

	w.set_focus()
	send_keys("^+{TAB}" if back else "^{TAB}")
	time.sleep(1)
	return box(app), w.window_text()


def open_document(app, w, name):
	"""Select ``name`` and choose File > Open: the box it showed (or None)."""
	D.select(w, name)
	G.menu(w, "#0->#0", wait=0.5)
	return box(app)


def import_files(app, w, folder, names):
	"""File > Import; open ``folder`` in the file dialog, then choose ``names`` together."""
	G.menu(w, "#0->#5", wait=0.5)
	dialog = X.wait_window(app, w, IMPORT_DIALOG)
	edit = dialog.child_window(class_name="Edit", found_index=0).wrapper_object()
	edit.set_edit_text(folder)
	G.press_keys(dialog, "{ENTER}")
	# Several names are quoted; one name is typed as it is (the dialog does not take a single quoted name).
	edit.set_edit_text(" ".join(f'"{name}"' for name in names) if len(names) > 1 else names[0])
	G.press_keys(dialog, "{ENTER}", wait=1)


def finish(app, w, d):
	print("close:", D.close(app, w))
	dx.kill_under(d)
