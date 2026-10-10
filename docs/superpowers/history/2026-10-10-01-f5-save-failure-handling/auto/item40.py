"""Item 40 (F-5): a pasted lone surrogate is saved as U+FFFD.

Usage: python item40.py <exe> <work folder>
alpha is open; the clipboard holds the UTF-16 code units 41 D83D 42 (A, a lone high
surrogate, B), which are pasted into the input; Ctrl+Tab; Ctrl+Shift+Tab back to alpha;
Ctrl+Tab again.
After F-5: no message; alpha.txt in the package holds 41 ef bf bd 42; the second switch
away from alpha leaves the package (members and st_mtime_ns) as it was; after a restart
alpha shows 'A\\ufffdB'.
Before F-5 (N-f4): 儲存文件失敗：'utf-8' codec can't encode character '\\ud83d' ... at
every switch, and Close is vetoed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f5gui import (  # noqa: E402
	D,
	close_and_answer,
	dx,
	leftovers,
	member,
	package,
	paste_text_with_lone_surrogate,
	setup_alpha_beta,
	switch,
	workspace,
)

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
paste_text_with_lone_surrogate(w)
print("input:", ascii(D.get_input(w)))
print("ctrl+tab:", switch(app, w))
print("alpha.txt:", member(alpha, "alpha.txt").hex(" "))
saved = package(alpha)
print("ctrl+shift+tab:", switch(app, w, back=True), "input:", ascii(D.get_input(w)))
print("ctrl+tab again:", switch(app, w))
print("alpha not rewritten:", package(alpha) == saved, "tmp:", leftovers(d))
print("close:", close_and_answer(app, w, []))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart:", D.docs(w), "title:", w.window_text(), "input:", ascii(D.get_input(w)))
print("close:", close_and_answer(app, w, []))
dx.kill_under(d)
