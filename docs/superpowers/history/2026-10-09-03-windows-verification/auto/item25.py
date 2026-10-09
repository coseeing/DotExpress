import sys, os, time, subprocess, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx, docs as D, dicts as X
d = r"D:\dxtest\auto24"; dd = os.path.join(d, "dictionary")
LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lock.py")
ORIG = "\ufefftext,braille,type\n戊己,⠑⠋,Braille\n".encode("utf-8")
P = os.path.join(dd, "bom_lf.csv")
dx.kill_under(d)
app, w = dx.launch(r"D:\dxtest\N\DotExpress.exe", d, fresh=False)

def state():
	b = open(P, "rb").read()
	kind = "ORIG" if b == ORIG else ("SAVED(CRLF,noBOM)" if b == ORIG[3:].replace(b"\n", b"\r\n") else f"OTHER {b!r}")
	return kind, sorted(os.listdir(dd))

def attrib(p):
	return subprocess.run(["cmd", "/c", "attrib", p], capture_output=True, text=True).stdout.strip()

def editor():
	mgr = X.windows(app, w).get("字典管理") or X.open_mgr(app, w)
	return X.open_editor(app, w, mgr, "bom_lf")

def ok_and_report(label, ed):
	msgs, still = X.editor_ok(app, w, ed)
	rows = X.editor_rows(ed) if still else None
	print(label, "msgs:", msgs, "editor still open:", still, "rows:", rows, "state:", state())
	return still

def cancel_editor():
	ed = X.windows(app, w).get("自訂字典管理器")
	if ed: X.btn(ed, "取消", "Cancel").click(); time.sleep(1)
	print("   after cancel windows:", list(X.windows(app, w)), X.popups(app, w))

def reset():
	subprocess.run(["attrib", "-r", "-h", P])
	open(P, "wb").write(ORIG)

# 25 lock (Excel-style: read, share read)
reset(); ed = editor()
z = subprocess.Popen([sys.executable, LOCK, P, "120", "r"]); time.sleep(2)
still = ok_and_report("25 locked:", ed)
subprocess.run(["taskkill", "/T", "/F", "/PID", str(z.pid)], capture_output=True); time.sleep(1)
if still:
	ok_and_report("25 after unlock:", X.windows(app, w)["自訂字典管理器"])
else:
	cancel_editor()
# 26 read-only
reset(); subprocess.run(["attrib", "+r", P]); ed = editor()
still = ok_and_report("26 +r:", ed)
subprocess.run(["attrib", "-r", P])
if still:
	ok_and_report("26 after -r:", X.windows(app, w)["自訂字典管理器"])
print("26 attrib:", attrib(P))
# 27 hidden
reset(); subprocess.run(["attrib", "+h", P]); ed = editor()
still = ok_and_report("27 +h:", ed)
print("27 attrib:", attrib(P))
if still: cancel_editor()
subprocess.run(["attrib", "-h", P])
# 28 10x OK with Defender
reset()
fails = 0
for i in range(10):
	ed = editor()
	msgs, still = X.editor_ok(app, w, ed)
	k, files = state()
	if msgs or still or k.startswith("OTHER") or len(files) != len(set(f for f in files if not f.endswith(".tmp"))):
		fails += 1; print("28 iter", i + 1, msgs, still, k, files)
		if still: cancel_editor()
print("28 failures:", fails, "state:", state())
# 29 ACL deny write
reset()
user = os.environ["USERNAME"]
print("29 icacls deny:", subprocess.run(["icacls", P, "/deny", f"{user}:(W)"], capture_output=True, text=True).stdout.strip().splitlines()[0])
ed = editor()
still = ok_and_report("29 deny W:", ed)
print("29 icacls now:", subprocess.run(["icacls", P], capture_output=True, text=True).stdout.strip())
if still: cancel_editor()
print("29 restore:", subprocess.run(["icacls", P, "/remove:d", user], capture_output=True, text=True).stdout.strip().splitlines()[0])
print("29 icacls final:", subprocess.run(["icacls", P], capture_output=True, text=True).stdout.strip())
mgr = X.windows(app, w).get("字典管理")
if mgr: X.close_mgr(app, w, mgr)
print("close:", D.close(app, w))
print("final:", state(), attrib(P))
