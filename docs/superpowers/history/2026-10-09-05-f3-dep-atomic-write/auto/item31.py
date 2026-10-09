"""Item 31 (F-3): renaming the non-open beta while beta.dep is read-only.

Usage: python item31.py <exe> <work folder>
After F-3, for the regular rename beta -> gamma and the case-only rename beta -> Beta:
儲存文件失敗：[Errno 13] Permission denied: '...\\beta.dep'; the list and the disk do not
change, no .tmp, beta.dep stays read-only; after a restart alpha and beta are listed.
Before F-3: regular [WinError 5] with gamma.dep and beta.dep both left; case-only renamed,
with a read-only .beta.dep.<random>.tmp left that the app cannot delete.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import D, attrib, dx, files, leftovers, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
beta = os.path.join(workspace(d), "beta.dep")
subprocess.run(["attrib", "+r", beta])
for new_name in ("gamma", "Beta"):
    print(f"== 31 rename beta -> {new_name}")
    before = D.ws_state(d)
    D.select(w, "beta")
    print("rename:", D.rename(app, w, new_name))
    D.cancel_open(app, w)
    print("docs:", D.docs(w), "diff:", D.diff(before, D.ws_state(d)), "files:", files(d), "tmp:", leftovers(d))
    print("attrib:", attrib(beta))
subprocess.run(["attrib", "-r", beta])
print("close:", D.close(app, w))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart docs:", D.docs(w), "files:", files(d))
print("close:", D.close(app, w))
