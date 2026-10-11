r"""Item 117 (F-12 D8): the text processing script returns None.

Usage: python safe_run.py item117.py <exe> <work folder>
dictionary\preprocessing.py: main(text) returns None. Types 甲乙 and runs Translation > Convert.
Prints the box.
Before F-12 (N-f11c): the English "main must return str, got NoneType."
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f12gui as H  # noqa: E402
from f12gui import D  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
H.preprocessing(d, "def main(text):\r\n    return None\r\n")
app, w, shown = H.start(d)
print(f"117 start: shown {shown} docs {D.docs(w)}")
H.set_source(w, "甲乙")
H.convert_menu(w)
print("117 convert:", H.box(app, d, timeout=30))
print("117 more boxes:", H.boxes(app, d, timeout=2))
H.finish(app, w, d)
