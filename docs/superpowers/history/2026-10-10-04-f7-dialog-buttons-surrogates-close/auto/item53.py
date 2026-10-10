"""Items 53, 56 and 57 (F-7, F-W9): the document name dialog and the message boxes.

Usage: python item53.py <exe> <work folder>
53: Add alpha; Add again, alpha: the "already exists" box (Enter), then the name dialog
    shown again (its buttons and name), Esc; the document list.
56: one OK box of each kind: Convert ("Conversion completed.", Esc); Help > About
    (Enter); Export All as BRL into <work folder>\\out56, where a folder named alpha.brl
    makes that document fail: the overwrite question (Alt+Y), then the summary (Enter).
57: Delete alpha: the question (Alt+N: kept), Delete again (Alt+Y: deleted); Export All
    as BRL into <work folder>\\out57, which already holds new.brl: the question (Alt+N).
Before F-7 (N-f6b): every OK box and the name dialog shown again are English (F-W9);
the Yes/No questions are the same.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f7gui as G  # noqa: E402
from f7gui import D, X, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = dx.launch(EXE, d)
print("53 add alpha:", D.add(app, w, "alpha"))
G.menu(w, "#0->#3")
dialog = X.wait_window(app, w, "新增文件")
dialog.child_window(class_name="Edit").wrapper_object().set_edit_text("alpha")
X.btn(dialog, "確定", "OK").click()
print("53 box:", G.answer_box(app, "enter"))
again = X.wait_window(app, w, "新增文件")
print("53 shown again: buttons", G.buttons(again), "name", repr(G.edit_text(again)))
G.press_keys(again, "{ESC}")
print("53 after esc: windows:", G.windows(app, w), "docs:", D.docs(w))

D.set_input(w, "abc")
G.menu(w, "#1->#0", wait=0.5)
print("56 convert:", G.answer_box(app, "esc", timeout=60))
G.menu(w, "#2->#1", wait=0.5)
about = G.answer_box(app, "enter")
about["content"] = about["content"].splitlines()[0] + " ..."
print("56 about:", about)
out56 = os.path.join(d, "out56")
os.makedirs(os.path.join(out56, "alpha.brl"))
G.menu(w, "#0->#7->#1", wait=0.5)
G.path_dialog(app, w, "匯出全部文件", out56)
print("56 overwrite question:", G.answer_box(app, "alt-y"))
print("56 summary:", G.answer_box(app, "enter"))
print("56 out56:", sorted(os.listdir(out56)), "windows:", G.windows(app, w))

D.select(w, "alpha")
G.menu(w, "#0->#1", wait=0.5)
print("57 delete, no:", G.answer_box(app, "alt-n"), "docs:", D.docs(w))
D.select(w, "alpha")
G.menu(w, "#0->#1", wait=0.5)
print("57 delete, yes:", G.answer_box(app, "alt-y"), "docs:", D.docs(w))
out57 = os.path.join(d, "out57")
os.makedirs(out57)
with open(os.path.join(out57, "new.brl"), "wb") as stream:
	stream.write(b"old")
G.menu(w, "#0->#7->#1", wait=0.5)
G.path_dialog(app, w, "匯出全部文件", out57)
print("57 overwrite question:", G.answer_box(app, "alt-n"))
print("57 boxes after no:", G.answer_box(app, "enter", timeout=2))
with open(os.path.join(out57, "new.brl"), "rb") as stream:
	print("57 out57:", sorted(os.listdir(out57)), "new.brl:", stream.read())
print("close:", D.close(app, w))
dx.kill_under(d)
