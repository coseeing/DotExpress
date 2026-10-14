r"""Item 128 (c) (F-13 D3, regression): a normal Close after a completed conversion.

Usage: python safe_run.py item128.py <exe> <work folder>
alpha (short, pending) is open, beta is short. Ctrl+Enter; the box 轉換完成。 (Enter); then
WM_CLOSE: what the close shows, the exit code (process handle), the packages and gui.log.
(Items 128 (a) and (b) are F-9 item 93 and F-7 item 59, run with their own scripts.)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f13gui as H  # noqa: E402
from f13gui import A, D, F9, G, dx  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = A.prepare(EXE, d)
F9.pending(d, "alpha", "alpha text")
A.package(d, "beta", "beta body", "⠃")
app, w, shown = H.start(d)
print(f"128c start: shown {H.placements(shown)} {H.state(w)}")
handle = F9.process_handle(app.process)
F9.convert(w)
print("128c box:", H.masked(d, F9.box(app, d, timeout=60)))
time.sleep(1)
print(f"128c after the box: {H.state(w)}")
print("128c close:", H.masked(d, D.close(app, w)))
print(f"128c exit code {H.exit_code(handle, 10)}")
print(f"128c alpha {F9.package(d, 'alpha')} | beta {F9.package(d, 'beta')} files {A.files(d)} gui.log {G.gui_log(d)}")
dx.kill_under(d)
