import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx, docs as D
EXE, d = r"D:\dxtest\N\DotExpress.exe", r"D:\dxtest\auto18"
ws = os.path.join(d, "workspace")
dx.kill_under(d)
app, w = dx.launch(EXE, d, fresh=False)
start = D.ws_state(d)
print("start:", start)
names = ["alpha", "Alpha"]
cur = [n for n in D.docs(w) if n.lower() == "alpha"][0]
fails = 0
for i in range(10):
	new = "Alpha" if cur == "alpha" else "alpha"
	D.select(w, cur)
	r = D.rename(app, w, new)
	files = os.listdir(ws)
	ok = new in D.docs(w) and f"{new}.dep" in files
	if not ok or r[1] or r[2]:
		fails += 1
	print(i + 1, cur, "->", new, "ok" if ok else "FAIL", r[1:] if (r[1] or r[2]) else "", files)
	if ok:
		cur = new
print("failures:", fails)
print("close:", D.close(app, w))
end = D.ws_state(d)
print("end:", end, "content same (ignoring name):", sorted(v for v in start.values()) == sorted(v for v in end.values()))
