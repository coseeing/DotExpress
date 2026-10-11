"""Items 99 and 100 (F-11 D3, D7): Cancel, Esc and the close box ask only after a change.

Usage: python item99.py <exe> <work folder>
alpha.csv holds two rows. 99: open it, add x / ⠭; press Esc in the editor: the box, Esc
in it; press Cancel (the button has the focus): the box, its close box; press Alt+F4 in
the editor: the box, Alt+D (Discard Changes). Each time the editor, its rows and the focus.
100: open alpha, Esc (no change): it closes at once. Open it again, delete row 1 (no
box), Cancel: the box, Alt+D. The file never changes.
Before F-11 (N-f9b): Esc, Cancel and Alt+F4 close the editor at once; x is lost.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

ALPHA = "text,braille,type\r\n甲乙,⠁⠃,Braille\r\n丙丁,⠉⠙,Braille\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"alpha.csv": ALPHA})
path = H.dictionary(d, "alpha")
before = H.state(path)


def editor():
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, "alpha")


def report(label):
	ed = H.X.windows(app, w).get(H.EDITOR)
	rows = H.X.editor_rows(ed) if ed is not None else None
	print(f"{label}: windows {H.windows(app, w)} rows {rows} focus {H.focused()} file {H.same(before, path)}")


ed = editor()
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
H.fill_entry(dialog, "x", "⠭")
H.press_button(dialog, "確定")
print("99 rows:", H.X.editor_rows(ed))
H.select_row(ed, 2)
H.keys(ed, "{ESC}")
print("99 Esc in the editor: box", H.next_box(app, "esc"))
report("99 after Esc in the box")
ed = editor()
H.press_button(ed, "取消")
print("99 Cancel: box", H.next_box(app, H.F.CLOSE_BOX))
report("99 after the close box of the box")
ed = editor()
H.keys(ed, "%{F4}")
print("99 Alt+F4 in the editor: box", H.next_box(app, "alt-d"))
report("99 after Alt+D")

ed = editor()
H.select_row(ed, 0)
H.keys(ed, "{ESC}")
print("100 Esc without a change: box", H.next_box(app, "esc", timeout=3))
report("100 after Esc")
ed = editor()
H.select_row(ed, 0)
H.press_button(ed, "刪除")
print("100 Delete: box", H.next_box(app, "esc", timeout=3), "rows", H.X.editor_rows(ed))
H.press_button(ed, "取消")
print("100 Cancel: box", H.next_box(app, "alt-d"))
report("100 after Alt+D")
print("files:", H.files_state(d))
H.finish(app, w, d)
