"""Items 85-88 and 93 (F-9 D1-D3, D5, D8): leaving the document that a conversion started from.

Usage: python item85.py <exe> <work folder> <85|86|87|88|93>
alpha holds a long text (pending), beta the short "beta body" with braille "⠃"; alpha is
open. Ctrl+Enter starts a conversion of alpha (about 15 s), then at once:
85: Ctrl+Tab to beta. Wait for the box; beta's editors; Ctrl+Tab back to alpha; Close;
    the packages; start again.
86: Ctrl+Tab and Ctrl+Shift+Tab (back to alpha) before the conversion ends.
87: Ctrl+O and import data\\imported.txt instead of Ctrl+Tab (the import opens it).
88: as 85, and then lock.py holds alpha.dep open (share read) until the box; unlock;
    Ctrl+Tab to alpha, Ctrl+Tab to beta; Close; the packages.
93: as 85, then WM_QUERYENDSESSION (ENDSESSION_LOGOFF) to the main window while the
    conversion runs; the box; Ctrl+Tab to alpha, Ctrl+Enter, and WM_ENDSESSION (wParam 1)
    while that conversion runs: the exit code, the files, gui.log.
Before F-9 (N-f8b2): the result goes to the document open when the conversion ends.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f9gui as H  # noqa: E402
from f9gui import A, B, D, F, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
H.pending(d, "alpha", H.long_text())
A.package(d, "beta", "beta body", "⠃")
app, w, shown = B.start(d)
print(f"{item} start: shown {shown} docs {D.docs(w)} {H.editors(w)}")
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
pid = app.process

H.convert(w)
if item == "87":
	imported = A.write(os.path.join(d, "data", "imported.txt"), "imported text".encode("utf-8"))
	H.keys(w, "^o")
	H.export_path(app, w, H.IMPORT_DIALOG, imported)
else:
	H.keys(w, "^{TAB}")
	if item == "86":
		H.keys(w, "^+{TAB}")
print(f"{item} while converting: docs {D.docs(w)} {H.editors(w)} box open {H.box_open(app)}")
holder = None
if item == "88":
	holder = F.lock(os.path.join(d, "workspace", "alpha.dep"), "r")
if item == "93":
	query = G.SessionMessage(w.handle, G.WM_QUERYENDSESSION)
	query.start()
	query.join(12)
	print(f"93 WM_QUERYENDSESSION: {H.call_state(query)} running {app.is_process_running()} box open {H.box_open(app)}")

print(f"{item} box: {H.box(app, d, timeout=90)}")
print(f"{item} after the box: {H.editors(w)}")
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
if holder is not None:
	F.unlock(holder)
print(f"{item} more boxes: {H.box(app, d, timeout=3)}")

if item in ("85", "88", "93"):
	H.keys(w, "^{TAB}")
	print(f"{item} Ctrl+Tab: {H.editors(w)} box {H.box(app, d, timeout=2)}")
if item == "88":
	H.keys(w, "^{TAB}")
	print(f"88 Ctrl+Tab: {H.editors(w)} box {H.box(app, d, timeout=2)}")
	print(f"88 alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
if item == "93":
	H.convert(w)
	print(f"93 converting again: box open {H.box_open(app)}")
	end = G.SessionMessage(w.handle, G.WM_ENDSESSION, wparam=1)
	end.start()
	end.join(12)
	print(f"93 WM_ENDSESSION: {H.call_state(end)} exit code {G.exit_code(pid, 5)}")
	print(f"93 files {A.files(d)} gui.log {G.gui_log(d)}")
	print(f"93 alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
	A.dx.kill_under(d)
	sys.exit(0)
print("close:", H.masked(d, D.close(app, w)))
print(f"{item} alpha.dep {H.package(d, 'alpha')} | beta.dep {H.package(d, 'beta')}")
print(f"{item} files {A.files(d)} gui.log {G.gui_log(d)}")
app, w, shown = B.start(d)
print(f"{item} restart: shown {shown} docs {D.docs(w)} {H.editors(w)}")
H.finish(app, w, d)
