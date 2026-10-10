"""Items 61-63 (F-7, F-5 review M-7): a lone surrogate in the source text.

Usage: python item61.py <exe> <work folder>
61: Add alpha. Type A U+FFFD B and convert: the braille of U+FFFD. Then paste A U+D83D B
    (f5gui.paste_text_with_lone_surrogate) and convert: the box, the braille (the same
    as for U+FFFD), and the source editor (it still holds the surrogate).
62: File > Export > HTML to <work folder>\\alpha.html: the box and the file's bytes.
63: File > Export All > HTML into the new folder <work folder>\\out63: the box and the files.
Before F-7 (N-f6b): the braille is that of the surrogate; the HTML export shows nothing,
and Export All stops at alpha without a summary.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, F, X, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
REPLACEMENT = chr(0xFFFD)
BLANK_CELL = chr(0x2800)


def code_points(text):
	return " ".join(f"U+{ord(character):04X}" for character in text)


def convert(app, w):
	"""Convert; return the box and the braille without its trailing blank cells."""
	G.menu(w, "#1->#0", wait=0.5)
	box = G.answer_box(app, "enter", timeout=60)
	return box, w.children(class_name="Edit")[1].window_text().rstrip(BLANK_CELL)


app, w = dx.launch(EXE, d)
print("add alpha:", D.add(app, w, "alpha"))
D.set_input(w, "A" + REPLACEMENT + "B")
box, replacement_braille = convert(app, w)
print("61 U+FFFD typed: box", box, "braille", repr(replacement_braille))
F.paste_text_with_lone_surrogate(w)
print("61 pasted:", code_points(D.get_input(w)))
box, braille = convert(app, w)
print("61 surrogate: box", box)
print("61 braille", repr(braille), "same as for U+FFFD:", braille == replacement_braille)
print("61 source editor after:", code_points(D.get_input(w)))

html = os.path.join(d, "alpha.html")
G.menu(w, "#0->#6->#2", wait=0.5)
G.path_dialog(app, w, "匯出文件", html)
print("62 export html:", G.answer_box(app, "enter", timeout=5))
if os.path.exists(html):
	with open(html, "rb") as stream:
		data = stream.read()
	print("62 alpha.html:", len(data) > 0, "EF BF BD:", b"\xef\xbf\xbd" in data, "ED A0 BD:", b"\xed\xa0\xbd" in data)
else:
	print("62 alpha.html: missing")

out63 = os.path.join(d, "out63")
os.makedirs(out63)
G.menu(w, "#0->#7->#2", wait=0.5)
G.path_dialog(app, w, "匯出全部文件", out63)
print("63 export all html:", G.answer_box(app, "enter", timeout=5))
print("63 out63:", {name: os.path.getsize(os.path.join(out63, name)) > 0 for name in sorted(os.listdir(out63))})
print("windows:", G.windows(app, w), "gui.log:", G.gui_log(d))
print("close:", D.close(app, w))
dx.kill_under(d)
