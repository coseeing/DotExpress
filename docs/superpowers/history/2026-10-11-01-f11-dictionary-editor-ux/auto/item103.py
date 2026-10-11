"""Items 103 and 106 (F-11 D2, D1, D14): adding entries in dictionaries with special rows.

Usage: python item103.py <exe> <work folder>
103: dict_badbopo (2026-10-09-03 data): Add 肚子 / ㄉㄨˋㄗ˙ / 注音; OK; Alt+S: the file.
106: tone1.csv holds 中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo (its last syllable is first tone): the
rows; Add 抹 / ㄇㄚ / 注音, typed without the tone space; OK: the file. Then convert
中心抹 with tone1 and with the default dictionary (both readings differ from the
default conversion, so the output shows that both rules are used).
Before F-11 (N-f9b): 103's Add is refused as a duplicate (F-4 D5); 106's row is hidden
and the Add shows the format error.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

TONE1 = "text,braille,type\r\n中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"dict_badbopo.csv": H.data("dict_badbopo.csv"), "tone1.csv": TONE1})


def add(ed, source, braille, type_label):
	"""Add through the real entry dialog: the box after OK (answered with Enter) and
	whether the entry dialog is still open (then it is cancelled)."""
	H.press_button(ed, "新增")
	dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
	H.fill_entry(dialog, source, braille, type_label)
	H.press_button(dialog, "確定")
	shown = H.next_box(app, "enter", timeout=3)
	still = H.X.windows(app, w).get(H.ADD_ENTRY)
	if still is not None:
		H.press_button(still, "取消")
	return shown, still is not None


path = H.dictionary(d, "dict_badbopo")
ed = H.editor(app, w, "dict_badbopo")
print("103 add:", add(ed, "肚子", "ㄉㄨˋㄗ˙", "注音"))
print("103 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("103 OK: box", H.next_box(app, "alt-s", timeout=3), "windows", H.windows(app, w))
print("103 dict_badbopo.csv:", repr(H.text(path)))

path = H.dictionary(d, "tone1")
ed = H.editor(app, w, "tone1")
print("106 rows:", H.X.editor_rows(ed))
print("106 add:", add(ed, "抹", "ㄇㄚ", "注音"))
print("106 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("106 OK: box", H.next_box(app, "enter", timeout=3), "windows", H.windows(app, w))
print("106 tone1.csv:", repr(H.text(path)))
H.D.select(w, "new")
H.set_dictionary(app, w, "tone1")
with_tone1 = H.convert(app, w, "中心抹")
H.set_dictionary(app, w, "default")
default = H.convert(app, w, "中心抹")
print("106 convert 中心抹 with tone1:", repr(with_tone1[0]), with_tone1[1], "| default:", repr(default[0]))
print("files:", H.files_state(d))
H.finish(app, w, d)
