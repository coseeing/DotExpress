"""Item 33 (F-3): Defender real-time protection on; 20 document switches, each after an edit.

Usage: python item33.py <exe> <work folder>
After F-3: 20 of 20 switches without a message and no .tmp; on disk alpha holds
"alpha edit 19" and beta "beta edit 20". A [WinError 5] would be the scanner holding the
package at that moment: record it (the edit stays in memory; the next action retries).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f3gui import D, files, leftovers, member_text, open_document, setup_alpha_beta, workspace  # noqa: E402

EXE, d = sys.argv[1], sys.argv[2]
status = subprocess.run(
    ["powershell", "-NoProfile", "-Command", "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
    capture_output=True,
    text=True,
)
print("Defender real-time protection:", status.stdout.strip() or status.stderr.strip())
app, w = setup_alpha_beta(EXE, d)
current = "alpha"
failures = 0
for step in range(1, 21):
    D.set_input(w, f"{current} edit {step}")
    target = "beta" if current == "alpha" else "alpha"
    messages = open_document(app, w, target)
    ok = not messages and w.window_text().startswith(f"{target} ")
    tmp = leftovers(d)
    if not ok or tmp:
        failures += 1
    print(step, current, "->", target, "ok" if ok else "FAIL", messages, tmp)
    if ok:
        current = target
print("failures:", failures)
print("close:", D.close(app, w))
ws = workspace(d)
print("alpha text:", repr(member_text(os.path.join(ws, "alpha.dep"), "alpha.txt")))
print("beta text:", repr(member_text(os.path.join(ws, "beta.dep"), "beta.txt")))
print("files:", files(d))
