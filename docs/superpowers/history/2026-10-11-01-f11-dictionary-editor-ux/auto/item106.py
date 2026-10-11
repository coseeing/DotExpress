"""Item 106 after the user's decision on review I-1 (F-11 D14, 2026-10-11).

Usage: python item106.py <exe> <work folder>
tone1.csv holds 中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo (its last syllable is first tone, with the tone
space) and 抹,ㄇㄚ,Bopomofo (the same, without the tone space). Before any edit, convert
中心抹末 with tone1 and with the default dictionary (all three readings differ from the
default conversion). Open the editor: the rows. Add 末 / ㄇㄚ / 注音 typed without the
tone space: the box; then the same entry with the space: the box, the rows. OK: the box,
answered with Enter (Back to Editing): the windows and the file; OK again, Alt+S (Remove
and Save): the file. Convert 中心抹末 again.
Expected after the decision (N-f11c): the row with the space is shown, the one without is
hidden, listed in the D1 box and ignored by conversion (抹 keeps the default reading);
'ㄇㄚ' is refused with the format error, 'ㄇㄚ ' is accepted and saved as typed.
Before F-11 (N-f9b): both rows are hidden, both Adds are refused, OK closes the editor
without a box, and 抹 converts through the fallback.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

NAME = "tone1"
WORD = "中心抹末"
TONE1 = "text,braille,type\r\n中心,ㄓㄨㄥˋㄒㄧㄣ ,Bopomofo\r\n抹,ㄇㄚ,Bopomofo\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"tone1.csv": TONE1})
path = H.dictionary(d, NAME)


def convert(label):
	H.close_manager(app, w)
	H.D.select(w, "new")
	H.set_dictionary(app, w, NAME)
	with_tone1 = H.convert(app, w, WORD)
	H.set_dictionary(app, w, "default")
	default = H.convert(app, w, WORD)
	print(f"106 convert {WORD} {label}: tone1", repr(with_tone1[0]), with_tone1[1], "| default:", repr(default[0]))


def try_entry(dialog, braille):
	"""Fill 末 / ``braille`` / 注音 and press OK: the box (answered with Enter) and whether
	the entry dialog is still open."""
	H.fill_entry(dialog, "末", braille, "注音")
	H.press_button(dialog, "確定")
	shown = H.next_box(app, "enter", timeout=3)
	still = H.X.windows(app, w).get(H.ADD_ENTRY)
	return shown, still


convert("before the edit")
before = H.state(path)
ed = H.editor(app, w, NAME)
print("106 rows:", H.X.editor_rows(ed))
H.press_button(ed, "新增")
dialog = H.entry_dialog(app, w, H.ADD_ENTRY)
shown, still = try_entry(dialog, "ㄇㄚ")
print("106 add ㄇㄚ (no tone space): box", shown, "| entry dialog open:", still is not None)
if still is not None:
	shown, still = try_entry(still, "ㄇㄚ ")
	print("106 add 'ㄇㄚ ' (tone space): box", shown, "| entry dialog open:", still is not None)
	if still is not None:
		H.press_button(still, "取消")
print("106 rows:", H.X.editor_rows(ed))
H.press_button(ed, "確定")
print("106 OK: box", H.next_box(app, "enter", timeout=3))
print("106 OK, Enter: windows", H.windows(app, w), "file", H.same(before, path))
ed = H.X.windows(app, w).get(H.EDITOR)
if ed is not None:
	H.press_button(ed, "確定")
	print("106 OK again: box", H.next_box(app, "alt-s", timeout=3))
	print("106 OK again, Alt+S: windows", H.windows(app, w))
print("106 tone1.csv:", repr(H.text(path)))
convert("after the save")
print("files:", H.files_state(d))
H.finish(app, w, d)
