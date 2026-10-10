"""Items 38 and 39 (F-5): Close after a failed save of a changed document.

Usage: python item38.py <exe> <work folder> <38|39>
alpha is open; "alpha edited" is typed; lock.py holds alpha.dep (share read); Ctrl+Tab;
then Close.
38: Esc: the app stays open with the edit. Close again, Enter (Retry) while the lock is
    held: the dialog again. The lock is released, Enter: the app exits. After a restart
    alpha holds the edit.
39: Alt+W (Close without saving): the app exits, the members of alpha.dep are unchanged
    since before the edit, no .tmp; after a restart alpha holds the old text.
Before F-5 (N-f4): Close shows the error box (確定 only) and is vetoed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f5gui import (  # noqa: E402
	D,
	close_and_answer,
	dx,
	files,
	leftovers,
	lock,
	member,
	package,
	setup_alpha_beta,
	switch,
	unlock,
	workspace,
)

EXE, d, item = sys.argv[1], sys.argv[2], sys.argv[3]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
before = package(alpha)
D.set_input(w, "alpha edited")
holder = lock(alpha, "r")
print("ctrl+tab:", switch(app, w))
print("input:", repr(D.get_input(w)))
if item == "38":
	dialogs, outcome = close_and_answer(app, w, ["esc"])
	print("close, esc:", outcome)
	for dialog in dialogs:
		print("  dialog:", dialog)
	print("input after esc:", repr(D.get_input(w)), "title:", w.window_text())
	dialogs, outcome = close_and_answer(app, w, ["enter", "enter"], between={1: lambda: unlock(holder)})
	print("close, enter while locked, unlock, enter:", outcome)
	for dialog in dialogs:
		print("  dialog:", dialog)
else:
	dialogs, outcome = close_and_answer(app, w, ["alt-w"])
	print("close, alt-w:", outcome)
	for dialog in dialogs:
		print("  dialog:", dialog)
	unlock(holder)
print(
	"alpha members changed:", package(alpha)[0] != before[0],
	"text:", repr(member(alpha, "alpha.txt").decode("utf-8")),
	"files:", files(d), "tmp:", leftovers(d),
)
app, w = dx.launch(EXE, d, fresh=False)
print("after restart:", D.docs(w), "title:", w.window_text(), "input:", repr(D.get_input(w)))
print("close:", close_and_answer(app, w, []))
dx.kill_under(d)
