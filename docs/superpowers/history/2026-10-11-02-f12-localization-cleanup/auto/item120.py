r"""Item 120 (F-12 Task 8, P1-3 defect 4): Delete All that fails and leaves no valid document.

Usage: python safe_run.py item120.py <exe> <work folder>
workspace\alpha.dep and beta.dep are valid; alpha is open. After the start, lockshare.py
holds beta.dep open without sharing, so deleting it fails and the reload finds it invalid.
File > Delete All, Yes (Alt+Y); then every box and the invalid-files dialog (Keep) in turn.
Prints what each showed, then the window title, the list, the editors and the workspace.
Before F-12 (N-f11c): the title stays `alpha - DotExpress`, the list is empty, no new.dep.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, D, G  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
A.package(d, "alpha", "alpha text", "⠁")
beta = A.package(d, "beta", "beta text", "⠃")
app, w, shown = H.start(d)
print(f"120 start: shown {shown} docs {D.docs(w)} {H.F9.editors(w)}")
holder = H.lock(beta, "none")
G.menu(w, "#0->#2", wait=0.5)
print("120 confirm:", H.masked(d, H.box(app, d, timeout=10, key="alt-y")))
print("120 then:", [H.masked(d, item) for item in H.settle(app, w, d, {}, seconds=40)])
H.unlock(holder)
print(f"120 after: docs {D.docs(w)} {H.F9.editors(w)}")
print(f"120 workspace: {A.files(d)}")
H.finish(app, w, d)
