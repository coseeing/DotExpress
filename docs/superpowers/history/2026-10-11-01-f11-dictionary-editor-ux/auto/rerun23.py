"""Items 23 and 24 again (F-11 D4, D5): OK without a change writes nothing; an edit is
written with the file's BOM.

Usage: python rerun23.py <exe> <work folder>
The 2026-10-09-03 data, imported through Dictionary Management: dict23 (no BOM, CRLF) and
bom_excel, bom_notepad, bom_lf (a BOM; bom_lf has LF line ends). For each: the count, the
rows, OK without a change (the file keeps its bytes and its modification time), then an
edit of row 1's braille (the cell ⠿ added) and OK: the file. Then 24's conversions with
each dictionary selected in Settings.
Before F-11 (N-f9b): every OK rewrites the file, without the BOM.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

NAMES = ("dict23", "bom_excel", "bom_notepad", "bom_lf")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d)
for name in NAMES:
	source = os.path.join(d, "data", f"{name}.csv")
	H.S.write(source, H.data(f"{name}.csv"))
	print(name, "import:", H.S.import_as(app, w, H.manager(app, w), source, name), "count:", H.count(app, w, name))
	path = H.dictionary(d, name)
	before = H.state(path)
	ed = H.editor(app, w, name)
	rows = H.X.editor_rows(ed)
	print(name, "rows:", rows)
	H.press_button(ed, "確定")
	print(name, "OK without a change: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w), "file", H.same(before, path))
	ed = H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, name)
	H.select_row(ed, 0)
	H.press_button(ed, "編輯")
	dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
	source_text, braille, _type = H.entry_fields(dialog)
	H.fill_entry(dialog, source_text, braille + "⠿")
	H.press_button(dialog, "確定")
	H.press_button(ed, "確定")
	print(name, "OK after the edit: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
	print(name, "file:", repr(H.text(path)))
H.close_manager(app, w)
H.D.select(w, "new")
for name, word, cells in (("default", "甲乙丙丁", None), ("bom_excel", "甲乙", "⠁⠃⠿"), ("bom_notepad", "丙丁", "⠉⠙⠿"), ("bom_lf", "戊己", "⠑⠋⠿")):
	H.set_dictionary(app, w, name)
	output, shown = H.convert(app, w, word)
	print("24 convert with", name, repr(word), "->", repr(output), "uses the dictionary:", (cells in output) if cells else "-", shown)
H.set_dictionary(app, w, "default")
print("files:", H.files_state(d))
H.finish(app, w, d)
