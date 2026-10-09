import sys, os, time, subprocess, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx, docs as D, dicts as X
d = r"D:\dxtest\auto24"; dd = os.path.join(d, "dictionary")
LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lock.py")
ORIG = "\ufefftext,braille,type\n戊己,⠑⠋,Braille\n".encode("utf-8")
P = os.path.join(dd, "bom_lf.csv")
app, w = dx.attach(d)
print('enabled', w.is_enabled(), list(X.windows(app, w)))

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

# 29 ACL deny write
reset()
user = os.environ["USERNAME"]
print("29 icacls deny:", subprocess.run(["icacls", P, "/deny", f"{user}:(WD,AD,WEA,WA)"], capture_output=True, text=True).stdout.strip().splitlines()[0])
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
