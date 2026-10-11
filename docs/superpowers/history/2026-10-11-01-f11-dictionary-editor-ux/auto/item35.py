"""Item 35 again (F-11 D1, D2, D13): dict_badbopo.csv through Dictionary Management and the editor.

Usage: python item35.py <exe> <work folder>
As F-4's item 35, with the expectations of F-11. Import dict_badbopo.csv (2026-10-09-03
data); convert 肚子數學 with it. 35a: OK: the box lists the two hidden rows; Back to
Editing (Alt+B) keeps the file; OK again, Remove and Save (Alt+S): 臺北 only; convert
again. 35b: Add 肚子 / ㄉㄨˋㄗ˙ / 注音: accepted; OK: written. 35c: delete 臺北, OK; the
count. 35d: restart: the count and the rows; Cancel.
Before F-11 (N-f9b, F-4): no box, the file is kept; the Add is refused; the hidden rows
stay through 35c and 35d.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

NAME = "dict_badbopo"
WORD = "肚子數學"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d)
source = os.path.join(d, "data", "dict_badbopo.csv")
H.S.write(source, H.data("dict_badbopo.csv"))
path = H.dictionary(d, NAME)
print("import:", H.S.import_as(app, w, H.manager(app, w), source, NAME), "count:", H.count(app, w, NAME))
H.close_manager(app, w)
H.D.select(w, "new")
H.set_dictionary(app, w, NAME)
first = H.convert(app, w, WORD)
print("convert 1:", repr(first[0]), first[1])


def editor():
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, NAME)


before = H.state(path)
ed = editor()
print("35a rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("35a OK: box", H.next_box(app, "alt-b", timeout=3))
print("35a after Alt+B: windows", H.windows(app, w), "file", H.same(before, path))
ed = editor()
H.press_button(ed, "確定")
print("35a OK again: box", H.next_box(app, "alt-s", timeout=3) is not None, "windows", H.windows(app, w))
print("35a file:", repr(H.text(path)), "files:", sorted(os.listdir(H.dictionary(d))))
second = H.convert(app, w, WORD)
print("35a convert 2:", repr(second[0]), "same as convert 1:", second[0] == first[0])

ed = editor()
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
H.fill_entry(dialog, "肚子", "ㄉㄨˋㄗ˙", "注音")
H.press_button(dialog, "確定")
print("35b add: box", H.next_box(app, "enter", timeout=3), "entry dialog open:", H.ADD_ENTRY in H.windows(app, w))
print("35b rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("35b OK: box", H.next_box(app, "alt-s", timeout=3), "windows", H.windows(app, w))
print("35b file:", repr(H.text(path)))

ed = editor()
H.select_row(ed, 0)
H.press_button(ed, "刪除")
print("35c rows after delete:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("35c OK: box", H.next_box(app, "alt-s", timeout=3), "windows", H.windows(app, w))
print("35c file:", repr(H.text(path)), "count:", H.count(app, w, NAME))
H.close_manager(app, w)
print("close:", H.D.close(app, w))

app, w = H.dx.launch(EXE, d, fresh=False)
print("35d count:", H.count(app, w, NAME))
ed = editor()
print("35d rows:", H.X.editor_rows(ed))
H.press_button(ed, "取消")
print("35d Cancel: box", H.next_box(app, "alt-d", timeout=3), "windows", H.windows(app, w))
print("35d file:", repr(H.text(path)), "files:", sorted(os.listdir(H.dictionary(d))))
H.finish(app, w, d)
