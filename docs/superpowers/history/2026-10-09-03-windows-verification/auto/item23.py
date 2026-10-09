import sys, os, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx, docs as D, dicts as X
def h(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] if os.path.exists(p) else None
for v in ("B", "N"):
	d = rf"D:\dxtest\auto23-{v}"
	dd = os.path.join(d, "dictionary")
	app, w = dx.launch(rf"D:\dxtest\{v}\DotExpress.exe", d)
	for src in ("dict23", "dict_badbopo"):
		mgr = X.windows(app, w).get("字典管理") or X.open_mgr(app, w)
		print(v, src, "import:", X.import_named(app, w, mgr, rf"D:\dxtest\data\{src}.csv"))
		p = os.path.join(dd, src + ".csv")
		before = open(p, "rb").read()
		mgr = X.windows(app, w).get("字典管理") or X.open_mgr(app, w)
		ed = X.open_editor(app, w, mgr, src)
		print(v, src, "rows:", X.editor_rows(ed))
		print(v, src, "ok:", X.editor_ok(app, w, ed))
		after = open(p, "rb").read()
		print(v, src, "changed:", before != after, "lines", before.count(b"\n"), "->", after.count(b"\n"), "bom:", after[:3] == b"\xef\xbb\xbf", "crlf:", after.count(b"\r\n") == after.count(b"\n"), "sha", h(p))
	mgr = X.windows(app, w).get("字典管理") or X.open_mgr(app, w)
	print(v, "mgr items:", X.mgr_items(mgr)[1])
	X.close_mgr(app, w, mgr)
	print(v, "close:", D.close(app, w))
	print(v, "dictionary dir:", os.listdir(dd))
