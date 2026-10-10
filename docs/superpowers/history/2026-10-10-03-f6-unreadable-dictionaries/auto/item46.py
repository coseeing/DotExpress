"""Item 46 (F-6): a dictionary whose ACL denies the user (F-W12's original reproduction).

Usage: python item46.py <exe> <work folder>
acl.csv is a readable UTF-8 dictionary, so the reason can only come from the ACL.
icacls <dictionary>\\acl.csv /deny %USERNAME%:(W) (W includes SYNCHRONIZE, so the file
cannot be opened at all); open Dictionary Management; select acl; 編輯; 匯出 to
<work folder>\\out.csv; the ACL is restored in every case.
Before F-6 (N-f5b): nothing opens.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f6gui as G  # noqa: E402
from f6gui import X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
acl = os.path.join(G.dictionary(d), "acl.csv")
out = os.path.join(d, "out.csv")
user = os.environ["USERNAME"]
app, w = G.start(EXE, d, put=("acl.csv",))
subprocess.run(["icacls", acl, "/deny", f"{user}:(W)"], capture_output=True)
try:
	mgr = G.open_mgr(app, w)
	if mgr is None:
		print("46: Dictionary Management did not open; windows:", G.windows(app, w), "boxes:", G.boxes(app, w))
	else:
		print("46 rows:", G.rows(mgr))
		X.mgr_select(mgr, "acl")
		print("46 acl reason:", G.reason(mgr))
		G.click(mgr, "編輯")
		print("46 edit:", G.boxes(app, w))
		print("46 windows:", G.windows(app, w))
		print("46 export:", G.export_to(app, w, mgr, out))
		print("46 out.csv exists:", os.path.exists(out), "windows:", G.windows(app, w))
finally:
	subprocess.run(["icacls", acl, "/remove:d", user], capture_output=True)
print("46 acl restored:", "DENY" not in subprocess.run(["icacls", acl], capture_output=True, text=True).stdout)
print("46 acl.csv unchanged:", G.sha(acl) == G.digest(G.FILES["acl.csv"]))
print("46 gui.log:", G.gui_log(d))
G.finish(app, w, d)
