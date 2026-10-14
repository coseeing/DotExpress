r"""Items 122-125 and 126 (plain, empty) (F-13 D2): the startup boxes after the main window.

Usage: python safe_run.py startup.py <exe> <work folder> <122|123|124|125|plain|empty>
122: F-8b item 70's workspace: an interrupted Rename of alpha to gamma (the moved-aside
     .alpha.dep._vw4x6f_.tmp, an hour old, and the staged .gamma.dep.mlw4jang.tmp).
123: F-8b item 73's workspace: alpha.dep with U+0000 in its text (one) and braille (one), beta.dep.
124: F-8a item 66's workspace: alpha.dep valid, bad.dep "not a zip"; Keep.
125: bad.dep "not a zip", the interrupted Rename of alpha (to gamma) whose text holds one
     U+0000, and a valid beta.dep; Keep.
plain: one valid alpha.dep (no box). empty: an empty workspace folder (first start).
f13gui.start answers each startup window and records whether the main window was visible,
whether the window is owned by it, and its title. Then the list, title, editors and focus,
and the files.
Before F-13 (N-f12b): every startup window comes before the main window is visible.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f13gui as H  # noqa: E402
from f13gui import A, B  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
if item == "122":
	B.leftover(d, ".alpha.dep._vw4x6f_.tmp", "alpha", "alpha body", "⠁⠃", age_s=3600)
	B.leftover(d, ".gamma.dep.mlw4jang.tmp", "gamma", "alpha body", "⠁⠃")
elif item == "123":
	A.package(d, "alpha", "first line\nsecond\x00 after\nthird", "⠁\x00⠃")
	A.package(d, "beta", "beta body", "⠃")
elif item == "124":
	A.package(d, "alpha", "alpha body")
	A.write(os.path.join(d, "workspace", "bad.dep"), b"not a zip")
elif item == "125":
	A.write(os.path.join(d, "workspace", "bad.dep"), b"not a zip")
	B.leftover(d, ".alpha.dep._vw4x6f_.tmp", "alpha", "alpha\x00body", "⠁", age_s=3600)
	B.leftover(d, ".gamma.dep.mlw4jang.tmp", "gamma", "alpha\x00body", "⠁")
	A.package(d, "beta", "beta body", "⠃")
elif item == "plain":
	A.package(d, "alpha", "alpha body", "⠁")
print(f"{item} files before: {A.files(d)}")
app, w, shown = H.start(d)
if app is None:
	print(f"{item} start failed: {H.masked(d, B.show(shown))}")
	A.dx.kill_under(d)
	sys.exit(1)
print(f"{item} shown: {H.masked(d, B.show(shown))}")
print(f"{item} placement: {H.placements(shown)}")
print(f"{item} replaced box content as expected: {B.replaced_boxes_ok(shown)}")
print(f"{item} {H.state(w)}")
print(f"{item} files after: {A.files(d)} gui.log {B.gui_log(d)}")
H.finish(app, w, d)
