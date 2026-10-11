"""Item 108 (F-11 review M-1): a dictionary whose header is not recognized is never emptied.

Usage: python safe_run.py item108.py <exe> <work folder>
caps.csv has the header Text,Braille,Type (as Excel may capitalize it) and two rows;
blank1.csv has a blank first line, then text,braille,type and a row. For each: open the
editor (its list), press OK (the button has the focus): the box, Enter; the windows, the
file (bytes and modification time) and the focus. Then Add 戊己 / ⠑⠋, OK: the same. Then
Cancel: the box, Alt+D (Discard Changes). Finally the file and the count in Dictionary
Management. After F-11's review fix: an error box says that the header is not recognized,
no box offers to remove rows, the editor stays open and the file keeps its bytes. Before
F-11 (N-f9b), OK closes the editor and rewrites the file, so each step reopens it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

FILES = {
	"caps.csv": "Text,Braille,Type\r\n甲乙,⠁⠃,Braille\r\n丙丁,⠉⠙,Braille\r\n".encode("utf-8"),
	"blank1.csv": "\r\ntext,braille,type\r\n甲乙,⠁⠃,Braille\r\n".encode("utf-8"),
}
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, FILES)


def editor(name):
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, name)


def report(label, name, before):
	path = H.dictionary(d, name)
	print(f"{label}: windows {H.windows(app, w)} file {H.same(before, path)} focus {H.focused()}")


for name in ("caps", "blank1"):
	path = H.dictionary(d, name)
	before = H.state(path)
	print(f"108 {name} count:", H.count(app, w, name))
	ed = editor(name)
	print(f"108 {name} rows:", H.X.editor_rows(ed))
	H.press_button(ed, "確定")
	print(f"108 {name} OK: box", H.next_box(app, "enter"))
	report(f"108 {name} after the box", name, before)
	ed = editor(name)
	H.press_button(ed, "新增")
	dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
	H.fill_entry(dialog, "戊己", "⠑⠋")
	H.press_button(dialog, "確定")
	print(f"108 {name} rows after the Add:", H.X.editor_rows(ed))
	H.press_button(ed, "確定")
	print(f"108 {name} OK after the Add: box", H.next_box(app, "enter"))
	report(f"108 {name} after the box", name, before)
	ed = H.X.windows(app, w).get(H.EDITOR)
	if ed is not None:
		H.press_button(ed, "取消")
		print(f"108 {name} Cancel: box", H.next_box(app, "alt-d"))
		report(f"108 {name} after Alt+D", name, before)
	print(f"108 {name} file:", repr(H.text(path)), "count:", H.count(app, w, name))
	H.close_manager(app, w)
print("files:", H.files_state(d))
H.finish(app, w, d)
