r"""Item 111 (F-12 D3): the reasons of the Import Issues dialog.

Usage: python safe_run.py item111.py <exe> <work folder>
alpha (converted) is listed. File > Import with the "All supported" filter, the names of
data\\alpha.txt (listed), big5.txt (Big5 bytes), <40 x>.txt, locked.txt (held open
without sharing by F-8a's lockshare.py), broken.dep (not a zip) and foo.xyz typed
together. Shows the Import Issues lines, any box, the document list and the workspace.
Before F-12 (N-f11c): the English and raw Python texts.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, B, D  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
LONG = "x" * 40
d = H.prepare(EXE, d)
A.package(d, "alpha", "alpha text", "⠁")
data = os.path.join(d, "data")
H.write(os.path.join(data, "alpha.txt"), "duplicate".encode("utf-8"))
H.write(os.path.join(data, "big5.txt"), "臺北的文字".encode("cp950"))
H.write(os.path.join(data, f"{LONG}.txt"), b"long name")
locked = H.write(os.path.join(data, "locked.txt"), b"locked text")
H.write(os.path.join(data, "broken.dep"), b"not a zip")
H.write(os.path.join(data, "foo.xyz"), b"unknown type")
names = ["alpha.txt", "big5.txt", f"{LONG}.txt", "locked.txt", "broken.dep", "foo.xyz"]
app, w, shown = H.start(d)
print(f"111 start: shown {shown} docs {D.docs(w)}")
holder = H.lock(locked, "none")
try:
	B.import_files(app, w, data, names)
	lines = H.import_issues(app, w)
	print("111 import issues:")
	for line in lines or ["(no Import Issues dialog)"]:
		print("   ", H.masked(d, line))
	print(f"111 boxes: {H.boxes(app, d, timeout=2)}")
finally:
	H.unlock(holder)
print(f"111 docs: {D.docs(w)} workspace: {A.files(d)}")
H.finish(app, w, d)
