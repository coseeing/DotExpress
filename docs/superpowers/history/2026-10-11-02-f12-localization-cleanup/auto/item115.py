r"""Item 115 (F-12 D7): the failed conversion names its document.

Usage: python safe_run.py item115.py <exe> <work folder> <a|b|c>
dictionary\preprocessing.py: main(text) sleeps 5 s, then raises ValueError("boom"). alpha and
beta are pending documents; alpha is open.
a: Ctrl+Enter, then Ctrl+Tab at once to beta; wait for the box.
b: select beta in the list (alpha stays open), File > Export > BRL into <d>\out\beta.brl.
c: Ctrl+Enter and wait (no Ctrl+Tab).
Prints each box (title, main instruction, content) and the editors.
Before F-12 (N-f11c): a, b show the script's text alone; c is the same.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import A, B, D, F9, G  # noqa: E402

EXE, d, case = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
SCRIPT = "import time\r\n\r\n\r\ndef main(text):\r\n    time.sleep(5)\r\n    raise ValueError(\"boom\")\r\n"
d = H.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
F9.pending(d, "alpha", "alpha text")
F9.pending(d, "beta", "beta text")
H.preprocessing(d, SCRIPT)
app, w, shown = H.start(d)
print(f"115{case} start: shown {shown} docs {D.docs(w)} {F9.editors(w)}")
if case == "a":
	F9.convert(w)
	F9.keys(w, "^{TAB}")
	print(f"115a while converting: {F9.editors(w)}")
elif case == "b":
	D.select(w, "beta")
	G.menu(w, "#0->#6->#1", wait=0.5)
	F9.export_path(app, w, F9.EXPORT_DIALOG, os.path.join(out, "beta.brl"))
else:
	F9.convert(w)
print(f"115{case} box:", H.masked(d, F9.box(app, d, timeout=60)))
print(f"115{case} more boxes:", H.boxes(app, d, timeout=3))
print(f"115{case} {F9.editors(w)} alpha {F9.package(d, 'alpha')} beta {F9.package(d, 'beta')} out {A.listing(out)}")
H.finish(app, w, d)
