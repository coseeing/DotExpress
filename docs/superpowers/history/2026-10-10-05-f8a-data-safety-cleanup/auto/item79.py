"""Items 79-81 (F-8 D9-D11): config.json that cannot be used.

Usage: python item79.py <exe> <work folder> <79|80|81>
The font size is changed with Ctrl + one wheel notch up over the source editor (one point
more than the size the app read). The client id that the app adds at startup is shown
as <id>. A file that is not JSON is shown as its bytes.
79: config.json holds null. Start: the main window; config.json, config.json.bak and
    log\\config.log; change the font size; config.json and .bak again.
80: config.json with a UTF-8 BOM, font size 20 and width 30. Start; change the font size:
    config.json (BOM, CRLF, values), no .bak.
81: config.json (font size 20, width 30) held open by lockshare.py with share "w" (others
    may write but not read). Start; change the font size: config.json unchanged,
    config.log; release; close; start again; change the font size: the old values were read.
Before F-8 (N-f7): 79 does not start; 80 and 81 lose the settings.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8agui as A  # noqa: E402
from f8agui import D  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
GOOD = b'{\r\n  "view": {\r\n    "font_size": 20\r\n  },\r\n  "conversion": {\r\n    "width": 30\r\n  }\r\n}'
d = A.prepare(EXE, d)
path = os.path.join(d, "config.json")
backup = path + ".bak"
A.write(path, {"79": b"null", "80": b"\xef\xbb\xbf" + GOOD, "81": GOOD}[item])
original = A.sha(path)


def state(label, held=False):
	"""config.json (client id as <id>), config.json.bak and config.log.

	While lockshare.py holds config.json without read sharing, only its log is read.
	"""
	if held:
		log = [line.replace(d, "<d>") for line in A.config_log(d)]
		print(f"{item} {label}: config.json held open; config.json.bak {A.read(backup)!r} config.log {log}")
		return
	described = A.config(d)
	if described is not None and isinstance(described["json"], dict):
		client = described["json"].get("client")
		if isinstance(client, dict) and "id" in client:
			client["id"] = "<id>"
		described["json"] = json.dumps(described["json"], sort_keys=True, ensure_ascii=False)
	log = [line.replace(d, "<d>") for line in A.config_log(d)]
	print(f"{item} {label}: config.json {described} unchanged: {A.sha(path) == original}")
	print(f"{item} {label}: config.json.bak {A.read(backup)!r} config.log {log}")


holder = A.lock(path, share="w") if item == "81" else None
app, w, invalid = A.start(d)
if app is None:
	print(f"{item} start: {invalid}")
	print(f"{item} files: {A.listing(d)}")
	if holder is not None:
		A.unlock(holder)
	sys.exit(0)
time.sleep(2)
print(f"{item} start: main window, docs {D.docs(w)}")
state("after start", held=holder is not None)
A.wheel_up_with_ctrl(w)
state("after the font change", held=holder is not None)
if item == "81":
	A.unlock(holder)
	state("released")
	print("close:", D.close(app, w))
	app, w, invalid = A.start(d)
	time.sleep(2)
	A.wheel_up_with_ctrl(w)
	state("released, restarted, font changed")
print(f"{item} files: {A.listing(d)}")
A.finish(app, w, d)
