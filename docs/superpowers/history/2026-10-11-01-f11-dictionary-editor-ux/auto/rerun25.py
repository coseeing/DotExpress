"""Items 25 to 29 again (F-11 D4, D5): each OK follows an edit, so that OK writes.

Usage: python rerun25.py <exe> <work folder>
bom_lf.csv (2026-10-09-03 data: a BOM, LF) is reset before each item; an edit sets row
1's braille (⠑⠋ to ⠑⠋⠁, in 28 alternately ⠑⠋⠁ and ⠑⠋⠃) and OK saves. 25: the file is
held open with share read (lock.py); OK; unlock; OK. 26: read-only (attrib +r); OK; -r;
OK. 27: hidden (+h); OK. 28: ten edits and OKs with Defender on. 29: icacls denies the
user writing (WD,AD,WEA,WA); OK; the deny entry is removed again.
The state of the file: ORIG (as reset), SAVED(<braille>) (a BOM, CRLF, the edit) or OTHER.
Before F-11 (N-f9b): SAVED has no BOM, so the state shows OTHER.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

ORIG = H.data("bom_lf.csv")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"bom_lf.csv": ORIG})
P = H.dictionary(d, "bom_lf")


def state():
	with open(P, "rb") as stream:
		content = stream.read()
	if content == ORIG:
		kind = "ORIG"
	else:
		kind = f"OTHER {H.masked(d, H.text(P))!r}"
		for braille in ("⠑⠋⠁", "⠑⠋⠃"):
			if content == H.BOM + f"text,braille,type\r\n戊己,{braille},Braille\r\n".encode("utf-8"):
				kind = f"SAVED({braille})"
	return kind, sorted(os.listdir(H.dictionary(d)))


def attrib():
	return subprocess.run(["cmd", "/c", "attrib", P], capture_output=True, text=True).stdout.strip().replace(P, "<file>")


def reset():
	subprocess.run(["attrib", "-r", "-h", P])
	with open(P, "wb") as stream:
		stream.write(ORIG)


def edit(braille):
	"""Open the editor and set row 1's braille; the editor stays open."""
	ed = H.editor(app, w, "bom_lf")
	H.select_row(ed, 0)
	H.press_button(ed, "編輯")
	dialog = H.entry_dialog(app, w, H.EDIT_ENTRY)
	source, _braille, _type = H.entry_fields(dialog)
	H.fill_entry(dialog, source, braille)
	H.press_button(dialog, "確定")
	return ed


def ok(label):
	"""Press OK in the open editor; print the box (answered with Enter), whether the editor
	is still open and the state. Returns whether it is still open."""
	ed = H.X.windows(app, w)[H.EDITOR]
	H.press_button(ed, "確定")
	shown = H.next_box(app, "enter", timeout=3)
	still = H.EDITOR in H.windows(app, w)
	print(label, "box:", H.masked(d, shown), "editor open:", still, "state:", state())
	return still


def cancel():
	ed = H.X.windows(app, w).get(H.EDITOR)
	if ed is not None:
		H.press_button(ed, "取消")
		H.next_box(app, "alt-d", timeout=3)


# 25: held open by another program with share read (Excel)
reset()
edit("⠑⠋⠁")
holder = H.F.lock(P, "r")
still = ok("25 locked:")
H.F.unlock(holder)
if still:
	ok("25 after unlock:")
cancel()
# 26: read-only
reset()
subprocess.run(["attrib", "+r", P])
edit("⠑⠋⠁")
still = ok("26 +r:")
subprocess.run(["attrib", "-r", P])
if still:
	ok("26 after -r:")
print("26 attrib:", attrib())
cancel()
# 27: hidden
reset()
subprocess.run(["attrib", "+h", P])
edit("⠑⠋⠁")
ok("27 +h:")
print("27 attrib:", attrib())
cancel()
subprocess.run(["attrib", "-h", P])
# 28: ten saves with Defender's real-time protection on
reset()
failures = 0
for index in range(10):
	braille = ("⠑⠋⠁", "⠑⠋⠃")[index % 2]
	edit(braille)
	ed = H.X.windows(app, w)[H.EDITOR]
	H.press_button(ed, "確定")
	shown = H.next_box(app, "enter", timeout=2)
	kind, files = state()
	if shown or H.EDITOR in H.windows(app, w) or kind != f"SAVED({braille})" or any(name.endswith(".tmp") for name in files):
		failures += 1
		print("28 iteration", index + 1, H.masked(d, shown), kind, files)
		cancel()
print("28 failures:", failures, "state:", state())
# 29: the user may not write the file (F-W13)
reset()
user = os.environ["USERNAME"]
print("29 icacls deny:", subprocess.run(["icacls", P, "/deny", f"{user}:(WD,AD,WEA,WA)"], capture_output=True, text=True).stdout.strip().splitlines()[0].replace(P, "<file>"))
print("29 deny entries before:", "DENY" in subprocess.run(["icacls", P], capture_output=True, text=True).stdout.upper())
edit("⠑⠋⠁")
ok("29 deny:")
print("29 deny entries left:", "DENY" in subprocess.run(["icacls", P], capture_output=True, text=True).stdout.upper())
subprocess.run(["icacls", P, "/remove:d", user], capture_output=True)
cancel()
H.close_manager(app, w)
print("close:", H.D.close(app, w))
print("final:", state(), attrib())
H.dx.kill_under(d)
