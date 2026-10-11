"""Items 101 and 102 (F-11 D8, D9): duplicates in the entry dialog; the selected twin.

Usage: python item101.py <exe> <work folder>
twins.csv: text,braille,type,note / a,⠁,General,first / b,⠃,General, / a,⠁,General,third.
101: Add b / ⠃: the box, its owner; after Enter the entry dialog with its fields, the
focus and the selection of the source text; then c, OK: added. Cancel, Alt+D.
102: (1) select row 3, Edit, braille ⠉, OK: the rows; Cancel, Alt+D. (2) Open it again,
select row 3, Delete, OK: the file.
Before F-11 (N-f9b): the entry dialog closes, then the editor shows the box and the input
is lost; the Edit of row 3 is refused; Delete removes row 1 (the first equal row).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

TWINS = "text,braille,type,note\r\na,⠁,General,first\r\nb,⠃,General,\r\na,⠁,General,third\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"twins.csv": TWINS})
path = H.dictionary(d, "twins")
before = H.state(path)


def entry_state(title):
	dialog = H.X.windows(app, w).get(title)
	if dialog is None:
		return "closed"
	return f"open, fields {H.entry_fields(dialog)}, focus {H.focused()}, selection {H.source_selection(dialog)}"


def discard():
	ed = H.X.windows(app, w).get(H.EDITOR)
	if ed is None:
		return "no editor"
	H.press_button(ed, "取消")
	return H.next_box(app, "alt-d", timeout=3)


ed = H.editor(app, w, "twins")
print("101 rows:", H.X.editor_rows(ed))
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
H.fill_entry(dialog, "b", "⠃")
H.press_button(dialog, "確定")
print("101 OK with b: box", H.next_box(app, "enter"))
print("101 entry dialog:", entry_state(H.ADD_ENTRY))
dialog = H.X.windows(app, w).get(H.ADD_ENTRY)
if dialog is not None:
	H.fill_entry(dialog, "c", "⠉")
	H.press_button(dialog, "確定")
	print("101 OK with c: box", H.next_box(app, "enter", timeout=3), "entry dialog", entry_state(H.ADD_ENTRY))
print("101 rows:", H.X.editor_rows(H.X.windows(app, w)[H.EDITOR]))
print("101 Cancel: box", discard(), "windows", H.windows(app, w), "file", H.same(before, path))

ed = H.editor(app, w, "twins")
H.select_row(ed, 2)
H.press_button(ed, "編輯")
dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
print("102 entry dialog shows:", H.entry_fields(dialog))
H.fill_entry(dialog, "a", "⠉")
H.press_button(dialog, "確定")
print("102 (1) OK: box", H.next_box(app, "enter", timeout=3), "entry dialog", entry_state(H.EDIT_ENTRY))
dialog = H.X.windows(app, w).get(H.EDIT_ENTRY)
if dialog is not None:
	H.press_button(dialog, "取消")
print("102 (1) rows:", H.X.editor_rows(H.X.windows(app, w)[H.EDITOR]))
print("102 (1) Cancel: box", discard(), "windows", H.windows(app, w), "file", H.same(before, path))
ed = H.editor(app, w, "twins")
H.select_row(ed, 2)
H.press_button(ed, "刪除")
print("102 (2) rows after Delete:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("102 (2) OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("102 (2) twins.csv:", repr(H.text(path)))
print("files:", H.files_state(d))
H.finish(app, w, d)
