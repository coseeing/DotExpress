r"""Item 156 (F-18 D7, D-G, D8.2): a script that cannot be read and one that is not valid.

Usage: python safe_run.py item156.py <exe> <work folder>
script\locked.py (valid) is held open without read sharing by a helper process (F-8a's
lockshare.py, share "none"); script\broken.py has a syntax error. Script Management opens:
the rows; `locked` selected: the reason field; 編輯: the box (the dialog stays); `broken`
selected: the reason field; 編輯: the editor opens with the file's text; 取消 (no change)
closes it at once. The helper is ended afterwards.
Since the review fixes (N-f18c): the gui.log lines added by the 編輯 of `locked` (review M-3:
one, from the refresh after the box; two before) and the focus after the box.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import A, D, F9, X  # noqa: E402

BROKEN = b"def main(text)\n    return text\n"
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
locked = H.script(d, "locked", H.UPPER)
H.script(d, "broken", BROKEN)
app, w, shown = H.start(d)
print(f"156 start: shown {shown} docs {D.docs(w)}")
holder = A.lock(locked, share="none")
try:
	mgr = H.open_manager(app, w)
	print("156 rows:", H.rows(mgr))
	H.select(mgr, "locked")
	print("156 locked reason:", H.reason(mgr))
	print("156 locked buttons:", H.buttons(mgr))
	lines_before = len(H.script_log_lines(d))
	H.press(mgr, "編輯", wait=1)
	print("156 locked edit:", H.box(app, d))
	time.sleep(1)
	print("156 gui.log lines added by the edit of locked:", H.script_log_lines(d)[lines_before:], "focus", H.focus())
	print("156 windows after the box:", H.windows(app, w))
	H.select(mgr, "broken")
	print("156 broken reason:", H.reason(mgr))
	H.press(mgr, "編輯", wait=1.5)
	editor = X.wait_window(app, w, "broken")
	print("156 broken editor:", H.editor_state(editor))
	H.press(editor, "取消", "Cancel", wait=1.5)
	print("156 windows after 取消:", H.windows(app, w))
	print("156 boxes:", H.H12.boxes(app, d, timeout=2))
	H.press(mgr, "關閉", "Close")
finally:
	A.unlock(holder)
	time.sleep(0.5)
print("156 locked.py and broken.py unchanged:", H.script_files(d).get("locked.py") == H.UPPER, H.script_files(d).get("broken.py") == BROKEN)
print("156 gui.log lines about scripts:", [line.split("] ", 1)[-1] for line in (A.read(os.path.join(d, "log", "gui.log")) or b"").decode("utf-8", "replace").splitlines() if "script" in line])
H.close(app, w, d)
