"""Items 97 and 98 (F-11 D4, D5): OK writes only after a change and keeps the file's layout.

Usage: python item97.py <exe> <work folder>
extra.csv: a BOM, the header text,note,braille,type, a row with spaces around its fields
and the type Custom, CRLF. 97: open it, OK: no box, the file keeps its bytes and its
modification time. 98: open it, edit row 1's braille (⠁ to ⠁⠁), add Gamma / ⠛, OK: the
BOM, the header and the notes stay, the new row's note is empty, every row is stripped
and Custom is written as General. The same edit on bom_lf.csv (2026-10-09-03 data: a BOM
and LF line ends): the BOM stays, the line ends become CRLF.
Before F-11 (N-f9b): every OK rewrites the file without the BOM and drops the note column.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

EXTRA = H.BOM + "text,note,braille,type\r\n Alpha ,first, ⠁ ,Custom\r\nBeta,second,⠃,General\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"extra.csv": EXTRA, "bom_lf.csv": H.data("bom_lf.csv")})


def edit_first_row(ed, braille):
	H.select_row(ed, 0)
	H.press_button(ed, "編輯")
	dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
	print("   entry dialog shows:", H.entry_fields(dialog))
	source, _braille, _type = H.entry_fields(dialog)
	H.fill_entry(dialog, source, braille)
	H.press_button(dialog, "確定")


def add_row(ed, source, braille):
	H.press_button(ed, "新增")
	dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
	H.fill_entry(dialog, source, braille)
	H.press_button(dialog, "確定")


path = H.dictionary(d, "extra")
before = H.state(path)
ed = H.editor(app, w, "extra")
print("97 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("97 OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("97 file:", H.same(before, path), repr(H.text(path)))

ed = H.editor(app, w, "extra")
edit_first_row(ed, "⠁⠁")
add_row(ed, "Gamma", "⠛")
print("98 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("98 OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("98 extra.csv:", repr(H.text(path)))

path = H.dictionary(d, "bom_lf")
ed = H.editor(app, w, "bom_lf")
print("98 bom_lf rows:", H.X.editor_rows(ed))
edit_first_row(ed, "⠑⠋⠁")
H.press_button(ed, "確定")
print("98 bom_lf OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("98 bom_lf.csv:", repr(H.text(path)))
print("files:", H.files_state(d))
H.finish(app, w, d)
