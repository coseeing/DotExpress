"""Items 104 and 105 (F-11 D10, D11): a case-only rename; an Import source that is locked.

Usage: python item104.py <exe> <work folder>
104: select alpha in Settings; Dictionary Management, Rename alpha to Alpha: the boxes,
the list, the files, config.json; convert 甲乙 (alpha has 甲乙,⠁⠃,Braille).
105: Import data\\src.csv; once the file dialog has closed, lockx.py holds it without
sharing; name it src: the box; the files.
Before F-11 (N-f9b): 104 shows 字典「Alpha」已存在。 and the name dialog again (it is
cancelled); 105 shows the raw [Errno 13].
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f11gui as H  # noqa: E402

ALPHA = "text,braille,type\r\n甲乙,⠁⠃,Braille\r\n丙丁,⠉⠙,Braille\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
app, w = H.setup(EXE, d, {"alpha.csv": ALPHA})
H.D.select(w, "new")
H.set_dictionary(app, w, "alpha")
print("104 config before:", H.config_dictionary(d))
mgr = H.manager(app, w)
H.X.mgr_select(mgr, "alpha")
H.S.click(mgr, "重新命名", wait=0.5)
print("104 rename: boxes", H.S.name_dialog(app, w, "重新命名字典", "Alpha"))
again = H.X.windows(app, w).get("重新命名字典")
if again is not None:
	print("104 the name dialog is open again; cancelled")
	H.press_button(again, "取消")
print("104 list:", H.S.rows(H.manager(app, w)))
print("104 files:", sorted(os.listdir(H.dictionary(d))), "config:", H.config_dictionary(d))
H.close_manager(app, w)
print("104 convert 甲乙:", repr(H.convert(app, w, "甲乙")[0]))

source = os.path.join(d, "data", "src.csv")
H.S.write(source, ALPHA)
mgr = H.manager(app, w)
H.S.click(mgr, "匯入", wait=0.5)
H.S.file_dialog(app, w, "匯入字典", source)
# The file dialog does not open a file that no one may share, so the lock comes after it,
# as when another program takes the file while the name is typed.
holder = H.S.lock_none(source)
try:
	print("105 import: boxes", [H.masked(d, shown) for shown in H.S.name_dialog(app, w, "新增字典", "src")])
finally:
	H.S.unlock(holder)
print("105 list:", H.S.rows(H.manager(app, w)))
print("105 files:", H.files_state(d))
H.finish(app, w, d)
