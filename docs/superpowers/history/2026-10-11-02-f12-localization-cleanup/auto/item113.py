r"""Item 113 (F-12 D5): a name held by a workspace entry that is not in the document list.

Usage: python safe_run.py item113.py <exe> <work folder>
workspace\alpha.dep is valid; workspace\bad.dep is not a package (Keep Invalid Files at the
start keeps it, so it is not listed). File > Add BAD; File > Rename alpha to bad; File >
Import data\bad.txt. Prints each box and the name dialog that opens again, the Import
Issues lines, the document list and the workspace.
Before F-12 (N-f11c): the generic "already exists" texts.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, B, D  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
A.package(d, "alpha", "alpha text", "⠁")
bad = H.write(os.path.join(d, "workspace", "bad.dep"), b"not a zip")
H.write(os.path.join(d, "data", "bad.txt"), "bad text".encode("utf-8"))
before = A.sha(bad)
app, w, shown = H.start(d)
print(f"113 start: shown {shown} docs {D.docs(w)}")
box, again = A.name_prompt(app, w, "#0->#3", "新增文件", "BAD")
print("113 add BAD: box", H.masked(d, box), "name dialog again", again)
D.select(w, "alpha")
box, again = A.name_prompt(app, w, "#0->#4", "重新命名文件", "bad")
print("113 rename alpha to bad: box", H.masked(d, box), "name dialog again", again)
B.import_files(app, w, os.path.join(d, "data"), ["bad.txt"])
lines = H.import_issues(app, w)
print("113 import issues:", [H.masked(d, line) for line in lines] if lines else lines)
print(f"113 more boxes: {H.boxes(app, d, timeout=2)}")
print(f"113 docs: {D.docs(w)} workspace: {A.files(d)} bad.dep unchanged: {A.sha(bad) == before}")
H.finish(app, w, d)
