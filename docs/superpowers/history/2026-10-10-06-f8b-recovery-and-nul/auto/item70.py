"""Items 70-72 (F-8 D3, D4): packages that a crash left in temporary files.

Usage: python item70.py <exe> <work folder> <70|71|72>
70: an interrupted Rename of alpha to gamma: the moved-aside .alpha.dep._vw4x6f_.tmp (an
    hour old) and the staged .gamma.dep.mlw4jang.tmp (now, same content), no .dep. Start:
    what startup shows, the list, the text, the files; close; start again. Then (the F-8b
    plan's addition, spec Risks) change alpha's text, close and start again.
71: gamma.dep and the leftover .alpha.dep.7gdjw2yi.tmp of a completed Rename (same
    content, an hour old). Start: what startup shows; the list; the .tmp files.
72: alpha.dep and the leftover .alpha.dep.97dc8315c5cf865f.tmp of an interrupted Save
    (newer text). Start: what startup shows; alpha's text; the .tmp files.
Before F-8b (N-f8a2): 70 shows nothing and starts with a new default document.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8bgui as B  # noqa: E402
from f8bgui import A, D  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
if item == "70":
	B.leftover(d, ".alpha.dep._vw4x6f_.tmp", "alpha", "alpha body", "⠁⠃", age_s=3600)
	B.leftover(d, ".gamma.dep.mlw4jang.tmp", "gamma", "alpha body", "⠁⠃")
elif item == "71":
	A.package(d, "gamma", "gamma body", "⠛")
	B.leftover(d, ".alpha.dep.7gdjw2yi.tmp", "alpha", "gamma body", "⠛", age_s=3600)
elif item == "72":
	A.package(d, "alpha", "saved text", "⠁")
	B.leftover(d, ".alpha.dep.97dc8315c5cf865f.tmp", "alpha", "newer text", "⠁")
before = B.temporary_files(d)


def state(label, app, w, shown):
	print(f"{item} {label}: shown {B.show(shown)}")
	print(f"{item} {label}: docs {D.docs(w)} title {w.window_text()!r} input {B.show(D.get_input(w))}")
	left = B.temporary_files(d)
	print(f"{item} {label}: files {A.files(d)} .tmp left unchanged: {all(before.get(name) == sha for name, sha in left.items())}")


app, w, shown = B.start(d)
state("start", app, w, shown)
print("close:", D.close(app, w))
app, w, shown = B.start(d)
state("restart", app, w, shown)
if item == "70":
	if D.docs(w) == ["alpha"]:
		D.set_input(w, "alpha edited")
		print("close:", D.close(app, w))
		app, w, shown = B.start(d)
		state("alpha edited, restart", app, w, shown)
	else:
		print("70 alpha is not listed; nothing edited")
B.finish(app, w, d)
