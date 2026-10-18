r"""Item 147 (F-18 D-A, D12): the legacy dictionary\preprocessing.py is not run any more.

Usage: python safe_run.py item147.py <exe> <work folder>
dictionary\preprocessing.py upper-cases its input; alpha is pending. Convert `abc`, then
`ABC`: on N-f18 the two Braille results differ (the script does not run), on N-f14b they
are the same (it runs). The file keeps its bytes. config.json before and after a Settings
Apply (on N-f18 the Apply writes selected_script).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import A, D, F9  # noqa: E402

LEGACY = b"def main(input):\n    return input.upper()\n"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
legacy = H.write(os.path.join(d, "dictionary", "preprocessing.py"), LEGACY)
app, w, shown = H.start(d)
print(f"147 start: shown {shown} docs {D.docs(w)}")
box, lower = H.convert(app, w, d, "abc")
print(f"147 convert abc: box {box} braille {lower!r}")
box, upper = H.convert(app, w, d, "ABC")
print(f"147 convert ABC: box {box} braille {upper!r}")
print("147 abc gives the Braille of ABC (the script ran):", lower == upper)
print("147 preprocessing.py keeps its bytes:", A.read(legacy) == LEGACY)
print("147 script folder:", sorted(H.script_files(d) or {}))
print("147 config.json conversion before Apply:", H.config(d))
dialog = H.settings(app, w)
H.press(dialog, "套用", "Apply")
H.press(dialog, "取消", "Cancel")
print("147 config.json conversion after Apply:", H.config(d))
H.close(app, w, d)
