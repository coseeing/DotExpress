r"""Item 143 (F-14 D2-D4, regression): the texts that were translated at import.

Usage: python safe_run.py item143.py <exe> <work folder>
dictionary\types.csv has one row of each type (General, Bopomofo, Braille); alpha is open.
(a) Help > About: the box (title, main instruction, content, owner).
(b) Translation > Settings: the title, the category list and the shown panel with its
    accessible description (UIA LegacyIAccessible.Description); then Ctrl+Tab twice, the
    same each time; Cancel.
(c) Dictionary Management > Edit types: the rows (the Type column); Add: the Type choice
    items and the selected one; Cancel twice.
Expected the same on N-f14 as before F-14 (N-f12b): every text in zh_TW.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f14gui as H  # noqa: E402
from f14gui import A, D, F9, H12  # noqa: E402

TYPES = "text,braille,type\r\n甲乙,⠁⠃,General\r\n抹,ㄇㄚˇ,Bopomofo\r\n丙,⠉,Braille\r\n".encode("utf-8")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = A.prepare(EXE, d)
H12.dictionary(d, "types", TYPES)
A.package(d, "alpha", "alpha body", "")
app, w, shown = H12.start(d)
print(f"143 start: shown {shown} docs {D.docs(w)} {F9.editors(w)}")
print("143a about:", H.about(app, w, d))
dialog = H12.settings(app, w)
print("143b settings:", H.settings_view(dialog))
for step in (1, 2):
	H.ctrl_tab(dialog)
	print(f"143b after Ctrl+Tab {step}:", H.settings_view(dialog))
H12.press(dialog, "取消", "Cancel")
print("143b boxes after Cancel:", H12.boxes(app, d, timeout=2))
print("143c editor:", H.editor_types(app, w, "types"))
H.finish(app, w, d)
