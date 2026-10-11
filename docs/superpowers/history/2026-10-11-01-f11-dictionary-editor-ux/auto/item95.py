"""Items 95 and 96 (F-11 D1, D13): dict_badbopo.csv and the box that lists its hidden rows.

Usage: python item95.py <exe> <work folder>
Import dict_badbopo.csv (2026-10-09-03 data: 臺北 and two Bopomofo rows that do not
parse). 96: select it in Settings and convert 肚子數學, and the same with the default
dictionary. 95: open the editor and press OK (the button has the focus): the box; Esc
in it; OK again, Enter; OK again, Alt+F4; each time the editor, the file and the focus.
Then OK and Alt+S (Remove and Save): the file and the count. 96 again: the conversion.
Before F-11 (N-f9b) there is no box: OK closes the editor and keeps the file (F-4), so
each step reopens the editor.
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
print("95 import:", H.S.import_as(app, w, H.manager(app, w), source, NAME))
print("95 imported identical:", H.state(path)[:2] == H.state(source)[:2], "count:", H.count(app, w, NAME))
H.close_manager(app, w)
H.D.select(w, "new")
H.set_dictionary(app, w, NAME)
first = H.convert(app, w, WORD)
H.set_dictionary(app, w, "default")
default = H.convert(app, w, WORD)
print("96 before the save:", repr(first[0]), first[1], "| default:", repr(default[0]), "| equal:", first[0] == default[0])


def editor():
	return H.X.windows(app, w).get(H.EDITOR) or H.editor(app, w, NAME)


before = H.state(path)
for label, key in (("95a Esc", "esc"), ("95b Enter", "enter"), ("95c Alt+F4", "alt-f4")):
	ed = editor()
	if label.startswith("95a"):
		print("95 rows:", H.X.editor_rows(ed))
	H.press_button(ed, "確定")
	described = H.next_box(app, key)
	print(f"{label}: box {described}")
	print(f"{label}: windows {H.windows(app, w)} file {H.same(before, path)} focus {H.focused()}")
ed = editor()
H.press_button(ed, "確定")
print("95d Alt+S: box", H.next_box(app, "alt-s"))
print("95d Alt+S: windows", H.windows(app, w), "file", repr(H.text(path)), "count:", H.count(app, w, NAME))
H.set_dictionary(app, w, NAME)
second = H.convert(app, w, WORD)
print("96 after the save:", repr(second[0]), second[1], "| equal to default:", second[0] == default[0], "| equal to before:", second[0] == first[0])
H.set_dictionary(app, w, "default")
print("files:", H.files_state(d))
H.finish(app, w, d)
