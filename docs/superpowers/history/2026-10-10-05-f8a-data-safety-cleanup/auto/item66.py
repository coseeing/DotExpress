"""Items 66-69 (F-8 D1, D2): a package that is on disk but not listed.

Usage: python item66.py <exe> <work folder> <66|67|68|69>
66: alpha.dep valid, bad.dep invalid; start, Keep. Add "bad": the box, the name dialog
    shown again (Esc); the list; bad.dep unchanged.
67: as 66. Rename alpha to "bad": the box, the dialog shown again (Esc); then Rename
    alpha to "Alpha" (case only): renamed.
68: as 66. Import bad.txt and ok.txt: the Import Issues dialog; the list; bad.dep unchanged.
69: only an invalid new.dep; start, Keep: the default document; new.dep unchanged.
Before F-8 (N-f7): bad.dep or new.dep is replaced without a message.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D, G, X  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
d = A.prepare(EXE, d)
kept = "new" if item == "69" else "bad"
kept_path = A.write(os.path.join(d, "workspace", f"{kept}.dep"), b"not a zip")
if item != "69":
	A.package(d, "alpha", "alpha body")
before = A.sha(kept_path)
app, w, invalid = A.start(d)
print(f"{item} start: invalid {invalid} docs {D.docs(w)} title {w.window_text()!r}")


def import_files(folder, names):
	"""File > Import; open ``folder`` in the file dialog, then choose ``names`` together."""
	G.menu(w, "#0->#5", wait=0.5)
	dialog = X.wait_window(app, w, "匯入文件")
	edit = dialog.child_window(class_name="Edit", found_index=0).wrapper_object()
	edit.set_edit_text(folder)
	G.press_keys(dialog, "{ENTER}")
	edit.set_edit_text(" ".join(f'"{name}"' for name in names))
	G.press_keys(dialog, "{ENTER}", wait=2)


if item == "66":
	box, again = A.name_prompt(app, w, "#0->#3", "新增文件", "bad")
	print("66 box:", box)
	print("66 shown again:", again)
elif item == "67":
	D.select(w, "alpha")
	box, again = A.name_prompt(app, w, "#0->#4", "重新命名文件", "bad")
	print("67 box:", box)
	print("67 shown again:", again)
	if "alpha" in D.docs(w):
		D.select(w, "alpha")
		print("67 case only:", A.name_prompt(app, w, "#0->#4", "重新命名文件", "Alpha"))
	else:
		print("67 case only: alpha is gone", D.docs(w))
elif item == "68":
	data = os.path.join(d, "data")
	A.write(os.path.join(data, "bad.txt"), b"bad text")
	A.write(os.path.join(data, "ok.txt"), b"ok text")
	import_files(data, ["bad.txt", "ok.txt"])
	issues = A.maybe_window(app, w, "匯入問題")
	if issues is None:
		print("68 import issues: none")
	else:
		print("68 import issues:", issues.child_window(class_name="ListBox").wrapper_object().item_texts())
		X.btn(issues, "確定", "OK").click()
		time.sleep(1)
print(f"{item} docs: {D.docs(w)} title: {w.window_text()!r} files: {A.files(d)} {kept}.dep unchanged: {A.sha(kept_path) == before}")
A.finish(app, w, d)
