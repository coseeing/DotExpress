"""Item 35 (F-4): dict_badbopo.csv through Dictionary Management and the entries editor.

Usage: python item35.py <exe> <work folder>
Reuses dx.py, docs.py and dicts.py of the 2026-10-09-03 Windows verification unchanged;
dx.launch deletes the work folder first. D:\\dxtest\\data\\dict_badbopo.csv is
auto/data/dict_badbopo.csv of that folder (sha256 c4324573...).

After F-4: count 1; the editor shows one row (臺北); an unchanged OK keeps the file
byte-identical, leaves no .tmp and keeps the conversion output of 肚子數學; Add of
肚子 / ㄉㄨˋㄗ˙ / 注音 shows 來源文字「肚子」已存在。 and the next OK keeps the file;
Delete of 臺北 and OK leave the header and the two Bopomofo rows, count 0; after a
restart the editor is empty and the file unchanged.
Before F-4 (B, N): the first OK leaves 2 lines, the second conversion differs, the Add
succeeds.
"""
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402
import dicts as X  # noqa: E402

SOURCE = r"D:\dxtest\data\dict_badbopo.csv"
NAME = "dict_badbopo"
MANAGER = "字典管理"
EDITOR = "自訂字典管理器"
WORD = "肚子數學"
HEADER_AND_HIDDEN_ROWS = "text,braille,type\r\n肚子,ㄉㄨˋ|ㄗ˙,Bopomofo\r\n數學,ㄕㄨˋ ㄒㄩㄝˊ,Bopomofo\r\n".encode("utf-8")

EXE, d = sys.argv[1], sys.argv[2]
dd = os.path.join(d, "dictionary")
P = os.path.join(dd, NAME + ".csv")


def read(path=P):
	with open(path, "rb") as handle:
		return handle.read()


def sha(data):
	return hashlib.sha256(data).hexdigest()


def listing():
	return sorted(os.listdir(dd))


def manager():
	return X.windows(app, w).get(MANAGER) or X.open_mgr(app, w)


def count():
	return [row for row in X.mgr_items(manager())[1] if row[0] == NAME]


def close_manager():
	mgr = X.windows(app, w).get(MANAGER)
	if mgr:
		X.close_mgr(app, w, mgr)


def editor():
	return X.open_editor(app, w, manager(), NAME)


def add_entry(ed, text, braille, type_label):
	"""Add through the real entry dialog; return the popups that follow (read and dismissed)."""
	X.btn(ed, "新增").click()
	entry_dialog = X.wait_window(app, w, "新增字典項目")
	controls = entry_dialog.wrapper_object().descendants()
	edits = [c for c in controls if c.class_name() == "Edit"]
	edits[0].set_edit_text(text)
	edits[1].set_edit_text(braille)
	[c for c in controls if c.class_name() == "ComboBox"][0].select(type_label)
	X.btn(entry_dialog, "確定", "OK").click()
	time.sleep(1.5)
	return X.popups(app, w, keep=(MANAGER, EDITOR))


def delete_first_row(ed):
	rows = [c for c in ed.wrapper_object().descendants() if c.class_name() == "SysListView32"][0]
	rows.get_item(0).select()
	time.sleep(0.5)
	X.btn(ed, "刪除").click()
	time.sleep(0.8)


def convert():
	close_manager()
	D.set_input(w, WORD)
	return X.convert(app, w)


source = read(SOURCE)
print("source sha256:", sha(source), "lines:", source.count(b"\n"))
app, w = dx.launch(EXE, d)
print("import:", X.import_named(app, w, manager(), SOURCE))
print("imported identical:", read() == source, "mgr:", count())
close_manager()
D.select(w, "new")
X.set_dictionary(app, w, NAME)
first, messages = convert()
print("convert 1:", repr(first), messages)

# 35a: an unchanged OK keeps the file and the conversion output.
ed = editor()
print("35a rows:", X.editor_rows(ed))
print("35a ok:", X.editor_ok(app, w, ed))
after = read()
print("35a identical:", after == source, "lines:", after.count(b"\n"), "sha256:", sha(after), "files:", listing())
second, messages = convert()
print("35a convert 2:", repr(second), messages, "same as convert 1:", second == first)

# 35b: an entry with the source text of a hidden row is refused.
ed = editor()
print("35b add:", add_entry(ed, "肚子", "ㄉㄨˋㄗ˙", "注音"))
print("35b rows:", X.editor_rows(ed))
print("35b ok:", X.editor_ok(app, w, ed))
print("35b identical:", read() == source, "files:", listing())

# 35c: deleting every shown row keeps the hidden rows.
ed = editor()
delete_first_row(ed)
print("35c rows after delete:", X.editor_rows(ed))
print("35c ok:", X.editor_ok(app, w, ed))
data = read()
print("35c header and hidden rows:", data == HEADER_AND_HIDDEN_ROWS, repr(data.decode("utf-8")), "files:", listing())
print("35c mgr:", count())
close_manager()
print("close:", D.close(app, w))

# 35d: after a restart the editor is empty and the file unchanged.
app, w = dx.launch(EXE, d, fresh=False)
print("35d mgr:", count())
ed = editor()
print("35d rows:", X.editor_rows(ed))
X.btn(ed, "取消", "Cancel").click()
time.sleep(1)
print("35d unchanged:", read() == HEADER_AND_HIDDEN_ROWS, "files:", listing())
close_manager()
print("close:", D.close(app, w))
