import sys, os, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx, docs as D, dicts as X
v = sys.argv[1]
d = rf"D:\dxtest\auto29-{v}"
app, w = dx.launch(rf"D:\dxtest\{v}\DotExpress.exe", d)
mgr = X.open_mgr(app, w)
print(v, "import:", X.import_named(app, w, mgr, r"D:\dxtest\data\dict23.csv"))
mgr = X.windows(app, w).get("字典管理") or X.open_mgr(app, w)
X.close_mgr(app, w, mgr)
P = os.path.join(d, "dictionary", "dict23.csv"); print(v, "files:", os.listdir(os.path.dirname(P)))
user = os.environ["USERNAME"]
subprocess.run(["icacls", P, "/deny", f"{user}:(W)"], capture_output=True)
try:
	w.set_focus(); w.menu_select("#1->#3"); time.sleep(3)
	print(v, "with unreadable dict, windows:", list(X.windows(app, w)), "popups:", X.popups(app, w), "main enabled:", w.is_enabled())
	m = X.windows(app, w).get("字典管理")
	if m: X.close_mgr(app, w, m)
finally:
	subprocess.run(["icacls", P, "/remove:d", user], capture_output=True)
print(v, "acl restored:", "DENY" not in subprocess.run(["icacls", P], capture_output=True, text=True).stdout)
print(v, "close:", D.close(app, w))
