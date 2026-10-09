"""Item 30 (F-3): regular rename of the non-open beta while beta.dep is held open.

Usage: python item30.py <exe> <work folder>
After F-3, for share r and rw: 儲存文件失敗：[WinError 32] ...: '...\\beta.dep' ->
'...\\.beta.dep.<random>.tmp'; the list and the disk do not change (no gamma.dep, no .tmp);
after a restart alpha and beta are listed and beta keeps its text.
Before F-3: gamma.dep and beta.dep both stayed on disk and both were listed after a restart.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import LOCK, D, dx, files, leftovers, member_text, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
app, w = setup_alpha_beta(EXE, d)
beta = os.path.join(workspace(d), "beta.dep")
for share in ("r", "rw"):
    print(f"== 30 share={share}")
    before = D.ws_state(d)
    lock = subprocess.Popen([sys.executable, LOCK, beta, "120", share])
    time.sleep(2)
    D.select(w, "beta")
    print("rename beta -> gamma while held open:", D.rename(app, w, "gamma"))
    D.cancel_open(app, w)
    print("docs:", D.docs(w), "diff:", D.diff(before, D.ws_state(d)), "files:", files(d), "tmp:", leftovers(d))
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(lock.pid)], capture_output=True)
    time.sleep(1)
print("close:", D.close(app, w))
app, w = dx.launch(EXE, d, fresh=False)
print("after restart docs:", D.docs(w), "files:", files(d))
print("beta text:", repr(member_text(beta, "beta.txt")))
print("close:", D.close(app, w))
