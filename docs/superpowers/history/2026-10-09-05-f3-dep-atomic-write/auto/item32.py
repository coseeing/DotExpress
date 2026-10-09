"""Item 32 (F-3): the open document's package is hidden; type, switch document, restart.

Usage: python item32.py <exe> <work folder>
After F-3: switching to beta saves alpha with no message, alpha.dep is no longer hidden,
no .tmp, and after a restart alpha has the typed text.
Before F-3: 儲存文件失敗：[Errno 13] Permission denied: '...\\alpha.dep', switch blocked.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import D, attrib, dx, leftovers, member_text, open_document, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
alpha = os.path.join(workspace(d), "alpha.dep")
subprocess.run(["attrib", "+h", alpha])
print("attrib before:", attrib(alpha))
D.set_input(w, "alpha typed while hidden")
print("switch to beta:", open_document(app, w, "beta"), "title:", w.window_text())
print("attrib after:", attrib(alpha), "tmp:", leftovers(d))
print("alpha text on disk:", repr(member_text(alpha, "alpha.txt")))
print("close:", D.close(app, w))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart docs:", D.docs(w))
print("open alpha:", open_document(app, w, "alpha"), "input:", repr(D.get_input(w)))
print("close:", D.close(app, w))
