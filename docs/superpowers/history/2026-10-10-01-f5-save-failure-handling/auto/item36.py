"""Items 36 and 37 (F-5): the open alpha is unchanged and its package cannot be written.

Usage: python item36.py <exe> <work folder> <readonly|r|rw>
readonly is item 36 (attrib +r alpha.dep); r and rw are item 37 (lock.py holds alpha.dep
with share read, or read+write). With alpha open and unchanged since the restart:
Ctrl+Tab, Add gamma, open alpha again, Close.
After F-5: no message; the switch and the Add work; the app exits; the members and
st_mtime_ns of alpha.dep are unchanged (and it is still R for readonly); no .tmp.
Before F-5 (N-f4): [Errno 13] (readonly) or [WinError 5] (r, rw) at every action, and
Close is vetoed (F-W10).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f5gui import (  # noqa: E402
	D,
	attrib,
	close_and_answer,
	dx,
	files,
	leftovers,
	lock,
	open_document,
	package,
	setup_alpha_beta,
	switch,
	unlock,
	workspace,
)

EXE, d, fault = sys.argv[1], sys.argv[2], sys.argv[3]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
holder = None
if fault == "readonly":
	subprocess.run(["attrib", "+r", alpha])
else:
	holder = lock(alpha, fault)
before = package(alpha)
print("attrib before:", attrib(alpha))
print("ctrl+tab:", switch(app, w))
print("add gamma:", D.add(app, w, "gamma"))
print("docs:", D.docs(w), "title:", w.window_text())
print("open alpha:", open_document(app, w, "alpha"), "title:", w.window_text())
print("close:", close_and_answer(app, w, []))
print("alpha unchanged:", package(alpha) == before, "attrib after:", attrib(alpha))
print("files:", files(d), "tmp:", leftovers(d))
if holder is not None:
	unlock(holder)
else:
	subprocess.run(["attrib", "-r", alpha])
dx.kill_under(d)
