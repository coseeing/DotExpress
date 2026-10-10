"""Items 89-92 (F-9 D4-D6): exports and Close while a conversion runs.

Usage: python item89.py <exe> <work folder> <89|90|91|92>
89: alpha (long, pending) is open. Ctrl+Enter, then Ctrl+S in the Braille Result editor
    and save <d>\\out\\alpha.brl: each box in turn; the editors; the file.
90: p1, p2 and p3 (long, pending); p1 is open. File > Export All > BRL into <d>\\out;
    during the first conversion, Ctrl+S in the Braille Result editor into <d>\\out2\\p1.brl:
    each box in turn; both folders.
91: File > Import data\\pend.txt (a pending document opens). File > Export > Dual View
    HTML into <d>\\out\\pend.html, then File > Export All > Dual View HTML into <d>\\outall:
    the boxes and what each file shows.
92: alpha (long, pending) is open. Ctrl+Enter; WM_CLOSE: the window stays; the box;
    WM_CLOSE again: the app exits; alpha.dep.
Before F-9 (N-f8b2): Ctrl+S starts a second conversion next to the running one (89, 90),
and with texts this long the app ends by itself; a pending document's HTML is the "No
conversion data" page (91); 92 is the same.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f9gui as H  # noqa: E402
from f9gui import A, B, D, G  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
out = os.path.join(d, "out")
os.makedirs(out)
if item in ("89", "92"):
	H.pending(d, "alpha", H.long_text())
elif item == "90":
	for name in ("p1", "p2", "p3"):
		H.pending(d, name, H.long_text())
app, w, shown = B.start(d)
print(f"{item} start: shown {shown} docs {D.docs(w)} {H.editors(w)}")
process = H.process_handle(app.process)


def boxes(label, first_timeout, count):
	"""Wait for up to ``count`` boxes, the first for ``first_timeout`` s and each next one for
	60 s; stop if the app ends by itself. Returns whether the app still runs."""
	timeout = first_timeout
	for number in range(1, count + 1):
		shown_box = H.next_box(app, d, process, timeout)
		if shown_box == "ended":
			print(f"{item} {label}: the app has ended by itself, exit code nonzero: {H.ended(process)}")
			return False
		print(f"{item} {label} box {number}: {shown_box}")
		if shown_box is None:
			return True
		print(f"{item} {label} after box {number}: {H.editors(w)}")
		timeout = 60
	return True


if item == "89":
	H.convert(w)
	w.children(class_name="Edit")[1].set_focus()
	H.keys(w, "^s")
	H.export_path(app, w, H.EXPORT_DIALOG, os.path.join(out, "alpha.brl"))
	print(f"89 exporting: box open {H.box_open(app)}")
	running = boxes("Ctrl+S", 90, 3)
	print(f"89 out {H.written(out)}")
	print(f"89 alpha.dep {H.package(d, 'alpha')}")
elif item == "90":
	out2 = os.path.join(d, "out2")
	os.makedirs(out2)
	G.menu(w, "#0->#7->#1", wait=0.5)
	H.export_path(app, w, H.EXPORT_ALL_DIALOG, out)
	w.children(class_name="Edit")[1].set_focus()
	H.keys(w, "^s")
	H.export_path(app, w, H.EXPORT_DIALOG, os.path.join(out2, "p1.brl"))
	print(f"90 exporting: box open {H.box_open(app)} out {H.written(out)} out2 {H.written(out2)}")
	running = boxes("Export All + Ctrl+S", 90, 3)
	print(f"90 out {H.written(out)}")
	print(f"90 out2 {H.written(out2)}")
elif item == "91":
	data = os.path.join(d, "data")
	A.write(os.path.join(data, "pend.txt"), "pending text\nsecond line".encode("utf-8"))
	B.import_files(app, w, data, ["pend.txt"])
	print(f"91 imported: docs {D.docs(w)} {H.editors(w)} pend.dep {H.package(d, 'pend')}")
	G.menu(w, "#0->#6->#2", wait=0.5)
	H.export_path(app, w, H.EXPORT_DIALOG, os.path.join(out, "pend.html"))
	print(f"91 export: box {H.box(app, d, timeout=30)}")
	print(f"91 pend.html {H.html_summary(os.path.join(out, 'pend.html'))}")
	outall = os.path.join(d, "outall")
	os.makedirs(outall)
	G.menu(w, "#0->#7->#2", wait=0.5)
	H.export_path(app, w, H.EXPORT_ALL_DIALOG, outall)
	print(f"91 export all: box {H.box(app, d, timeout=30)}")
	for name in sorted(os.listdir(outall)):
		print(f"91 outall\\{name} {H.html_summary(os.path.join(outall, name))}")
	print(f"91 {H.editors(w)} pend.dep {H.package(d, 'pend')}")
elif item == "92":
	import win32con

	H.convert(w)
	w.post_message(win32con.WM_CLOSE)
	time.sleep(2)
	print(f"92 WM_CLOSE while converting: running {app.is_process_running()} box open {H.box_open(app)} {H.editors(w)}")
	print(f"92 box: {H.box(app, d, timeout=90)}")
	print("close:", H.masked(d, D.close(app, w)))
	print(f"92 alpha.dep {H.package(d, 'alpha')} files {A.files(d)} gui.log {G.gui_log(d)}")
	A.dx.kill_under(d)
	sys.exit(0)
if item in ("89", "90") and not running:
	A.dx.kill_under(d)
else:
	H.finish(app, w, d)
