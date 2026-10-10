"""Item 82 (F-8 D6, D7): the dictionary files and the text-processing script.

Usage: python item82.py <exe> <work folder>
Dictionary Management: Add d1; Import data\\d2.csv (a UTF-8 file with a BOM, CRLF and
CJK text) as d2; select d1, Export over out\\d1.csv (which holds b"OLD"), overwrite Yes.
Text Processing: replace the script by one that returns text.upper(), Apply, then OK.
Prints the sha256 of every file in dictionary\\ and out\\ and preprocessing.py's bytes.
Before F-8 (N-f7) is the reference: the same bytes, no .tmp either way.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D, G, X  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
D2 = b"\xef\xbb\xbftext,braille,type\r\n" + "臺灣,⠞⠺,General\r\n".encode("utf-8")
SCRIPT = "def main(text):\r\n    return text.upper()\r\n"
WM_SETTEXT = 0x000C
d = A.prepare(EXE, d)
dictionary = os.path.join(d, "dictionary")
out = os.path.join(d, "out")
data = A.write(os.path.join(d, "data", "d2.csv"), D2)
A.write(os.path.join(out, "d1.csv"), b"OLD")
app, w, invalid = A.start(d)
print(f"82 start: invalid {invalid} docs {D.docs(w)}")

mgr = X.open_mgr(app, w)
X.btn(mgr, "新增").click()
dialog = X.wait_window(app, w, "新增字典")
dialog.child_window(class_name="Edit").wrapper_object().set_edit_text("d1")
X.btn(dialog, "確定", "OK").click()
time.sleep(1.5)
print("82 import d2:", X.import_named(app, w, mgr, data))
X.mgr_select(mgr, "d1")
X.btn(mgr, "匯出").click()
print("82 export d1, overwrite prompt:", A.save_dialog(app, w, "匯出字典", os.path.join(out, "d1.csv")))
print("82 export d1, box:", G.answer_box(app, "enter", timeout=3))
print("82 rows:", X.mgr_items(mgr)[1])
X.close_mgr(app, w, mgr)

G.menu(w, "#1->#2")
processing = G.window_titled(app, w, G.TEXT_PROCESSING)
editor = [c for c in processing.wrapper_object().descendants() if c.class_name().upper().startswith("RICHEDIT")][0]
editor.send_message(WM_SETTEXT, 0, SCRIPT)
X.btn(processing, "套用", "Apply").click()
time.sleep(1)
print("82 apply:", G.answer_box(app, "enter", timeout=2), "windows:", G.windows(app, w))
X.btn(processing, "確定", "OK").click()
time.sleep(1)
print("82 after OK: windows:", G.windows(app, w))

for folder in (dictionary, out):
	print(f"82 {os.path.basename(folder)}:", {name: A.sha(os.path.join(folder, name)) for name in A.listing(folder)})
print("82 preprocessing.py:", A.read(os.path.join(dictionary, "preprocessing.py")))
print("82 d2.csv equals the source:", A.read(os.path.join(dictionary, "d2.csv")) == D2)
print("82 out d1.csv equals dictionary d1.csv:", A.read(os.path.join(out, "d1.csv")) == A.read(os.path.join(dictionary, "d1.csv")))
A.finish(app, w, d)
