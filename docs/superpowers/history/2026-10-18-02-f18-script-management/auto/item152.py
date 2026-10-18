r"""Items 152-153 (F-18 D8.5): Import.

Usage: python safe_run.py item152.py <exe> <work folder>
<d>\source holds upper2.py (valid, a BOM and CRLF), x.txt (valid code; its name is typed
in the file dialog, past the *.py filter), cp950.py (not UTF-8) and bad.py (a syntax
error). 152: each one through 匯入, the file dialog and the name prompt (its name kept):
the box, and the script folder (upper2.py with the same bytes, nothing else copied).
153: script\upper.py exists; import upper.py as `upper`: the box, then the name prompt
again (its name), closed with 取消.
Since the review fixes (N-f18c): 匯入 is pressed with the keyboard focus on it, the name
prompt is optional (review M-2: x.txt is refused before it), and the focus is logged after
each import (review I-1: back in the list after a successful one).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import D, F9  # noqa: E402

UPPER2 = b"\xef\xbb\xbf" + "def main(text: str) -> str:\r\n    return text.upper() + '臺'\r\n".encode("utf-8")
SOURCES = (
	("upper2.py", UPPER2),
	("x.txt", b"def main(text):\n    return text\n"),
	("cp950.py", "def main(text):\n    return text + '臺'\n".encode("cp950")),
	("bad.py", b"def main(text)\n    return text\n"),
)
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
H.script(d, "upper", H.UPPER)
for name, data in SOURCES + (("upper.py", b"def main(text):\n    return text + '!'\n"),):
	H.write(os.path.join(d, "source", name), data)
app, w, shown = H.start(d)
print(f"152 start: shown {shown} docs {D.docs(w)}")
mgr = H.open_manager(app, w)
for name, _data in SOURCES:
	H.press_focused(mgr, "匯入", wait=1)
	H.file_dialog(app, w, H.IMPORT, os.path.join(d, "source", name))
	if H.maybe_window(app, w, H.ADD, timeout=3) is None:
		shown_name = "<no name prompt>"
	else:
		shown_name = H.name_prompt(app, w, H.ADD, os.path.splitext(name)[0])
	print(f"152 {name}: name prompt {shown_name!r}, box {H.box(app, d, timeout=4)}, focus {H.focus()}")
files = H.script_files(d)
print("152 script folder:", sorted(files), "upper2.py has the source's bytes:", files.get("upper2.py") == UPPER2)
print("152 rows:", H.rows(mgr), "selected", H.selected_row(mgr))
H.press(mgr, "匯入", wait=1)
H.file_dialog(app, w, H.IMPORT, os.path.join(d, "source", "upper.py"))
print("153 name prompt shows:", repr(H.name_prompt(app, w, H.ADD, "upper")))
print("153 box:", H.box(app, d, timeout=4))
again = H.maybe_window(app, w, H.ADD, timeout=5)
if again is None:
	print("153 the name prompt did not open again")
else:
	print("153 name prompt again with:", repr(again.child_window(class_name="Edit").wrapper_object().window_text()))
	H.press(again, "取消", "Cancel")
print("153 focus after 取消:", H.focus())
print("153 script\\upper.py unchanged:", H.script_files(d).get("upper.py") == H.UPPER)
H.press(mgr, "關閉", "Close")
H.close(app, w, d)
