r"""Item 121 (F-13 D1): the focus after the failure box of a conversion.

Usage: python safe_run.py item121.py <exe> <work folder> <a|b>
dictionary\preprocessing.py: main(text) sleeps 5 s, then raises ValueError("boom") (F-12 item
115). alpha and beta are pending documents; alpha is open.
a: Ctrl+Enter in alpha's source editor, then Ctrl+Tab at once to beta; wait for the box, Enter.
b: Ctrl+Enter and wait (no Ctrl+Tab); the box, Enter.
Prints the focus (GetGUIThreadInfo, mapped to the main window's editors) before the
conversion, while it runs, and 1 s after the box closed, with the UIA focused element.
Before F-13 (N-f12b): in (a) the focus stays in the Braille Result editor.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f13gui as H  # noqa: E402
from f13gui import A, D, F9, H12  # noqa: E402

EXE, d, case = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
SCRIPT = "import time\r\n\r\n\r\ndef main(text):\r\n    time.sleep(5)\r\n    raise ValueError(\"boom\")\r\n"
d = A.prepare(EXE, d)
F9.pending(d, "alpha", "alpha text")
F9.pending(d, "beta", "beta text")
H12.preprocessing(d, SCRIPT)
app, w, shown = H.start(d)
print(f"121{case} start: shown {H.placements(shown)} {H.state(w)}")
F9.convert(w)
if case == "a":
	F9.keys(w, "^{TAB}")
print(f"121{case} while converting: docs {D.docs(w)} {F9.editors(w)} focus {H.focus(w)}")
print(f"121{case} box:", H.masked(d, F9.box(app, d, timeout=60)))
time.sleep(1)
print(f"121{case} after the box: {H.state(w)}")
print(f"121{case} more boxes:", H12.boxes(app, d, timeout=3))
print(f"121{case} alpha {F9.package(d, 'alpha')} beta {F9.package(d, 'beta')}")
H.finish(app, w, d)
