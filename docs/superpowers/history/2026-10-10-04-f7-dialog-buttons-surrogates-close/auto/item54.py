"""Items 54 and 55 (F-7, F-W9): the dictionary name dialog and the dictionary editor.

Usage: python item54.py <exe> <work folder>
54: Dictionary Management: Add d1; Add again, d1: the "already exists" box (Enter), then
    the name dialog shown again (its buttons and name), Esc; the list.
55: Text Processing is opened and kept open; Dictionary Management, select d1, Edit: the
    editor's buttons; Add the entry x / 1; the editor's OK. Dictionary Management, Edit
    d1 again: the rows; Cancel. dictionary\\d1.csv. Then Text Processing's own Cancel.
    The same with the Settings dialog open instead (entry y / 2).
Before F-7 (N-f6b): English OK / Cancel in the box and the dialog shown again (F-W9); in
55 the editor's buttons are English and its OK closes without saving (the entry is lost).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, X, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d1 = os.path.join(d, "dictionary", "d1.csv")


def press_esc(win):
	from pywinauto.keyboard import send_keys

	win.set_focus()
	send_keys("{ESC}")
	time.sleep(1)


def add_dictionary(app, w, mgr, name):
	X.btn(mgr, "新增").click()
	dialog = X.wait_window(app, w, "新增字典")
	dialog.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	X.btn(dialog, "確定", "OK").click()
	time.sleep(1.5)


def add_entry_and_ok(app, w, mgr, text, braille):
	X.mgr_select(mgr, "d1")
	X.btn(mgr, "編輯").click()
	editor = X.wait_window(app, w, G.EDITOR)
	print("55 editor buttons:", G.buttons(editor))
	X.btn(editor, "新增").click()
	entry = X.wait_window(app, w, "新增字典項目")
	fields = [c for c in entry.wrapper_object().descendants() if c.class_name() == "Edit"]
	fields[0].set_edit_text(text)
	fields[1].set_edit_text(braille)
	X.btn(entry, "確定", "OK").click()
	time.sleep(1)
	print("55 editor rows before OK:", X.editor_rows(editor))
	X.btn(editor, "確定", "OK").click()
	time.sleep(1.5)
	print("55 after OK: windows:", G.windows(app, w), "boxes:", G.answer_box(app, "enter", timeout=1))


def reopen_rows(app, w):
	mgr = G.window_titled(app, w, G.MGR) if G.MGR in X.windows(app, w) else X.open_mgr(app, w)
	editor = X.open_editor(app, w, mgr, "d1")
	rows = X.editor_rows(editor)
	X.btn(editor, "取消", "Cancel").click()
	time.sleep(1)
	return rows


def with_modeless(app, w, menu_path, title_prefix, text, braille):
	G.menu(w, menu_path)
	modeless = G.window_titled(app, w, title_prefix)
	print(f"55 [{title_prefix}] open: buttons {G.buttons(modeless)}")
	mgr = X.open_mgr(app, w)
	add_entry_and_ok(app, w, mgr, text, braille)
	print(f"55 [{title_prefix}] reopened rows:", reopen_rows(app, w))
	with open(d1, "rb") as stream:
		print(f"55 [{title_prefix}] d1.csv:", stream.read())
	print(f"55 [{title_prefix}] its own buttons now: {G.buttons(modeless)}; windows: {G.windows(app, w)}")
	X.btn(modeless, "取消", "Cancel").click()
	time.sleep(1)
	print(f"55 [{title_prefix}] after its Cancel: windows:", G.windows(app, w))


app, w = dx.launch(EXE, d)
mgr = X.open_mgr(app, w)
add_dictionary(app, w, mgr, "d1")
print("54 first add: windows:", G.windows(app, w), "rows:", X.mgr_items(mgr)[1])
add_dictionary(app, w, mgr, "d1")
print("54 box:", G.answer_box(app, "enter"))
again = X.wait_window(app, w, "新增字典")
print("54 shown again: buttons", G.buttons(again), "name", repr(G.edit_text(again)))
press_esc(again)
print("54 after esc: windows:", G.windows(app, w), "rows:", X.mgr_items(mgr)[1])
X.close_mgr(app, w, mgr)

with_modeless(app, w, "#1->#2", G.TEXT_PROCESSING, "x", "1")
with_modeless(app, w, "#1->#4", G.SETTINGS_PREFIX, "y", "2")
print("close:", D.close(app, w))
dx.kill_under(d)
