import sys, time, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dx
exe, d, doc = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]

def convert_and_export(app, w, out):
	edits = w.children(class_name="Edit")
	before = edits[1].window_text()
	w.set_focus()
	w.menu_select("#1->#0")
	end = time.time() + 120
	while time.time() < end and not dx.dialogs(app):
		time.sleep(0.5)
	print("convert:", dx.dismiss(app))
	print("output changed:", edits[1].window_text() != before, "len", len(edits[1].window_text()))
	w.set_focus()
	w.menu_select("#0->#6->#1")
	dx.file_dialog(app, out)
	print("export:", dx.dismiss(app))
	print(os.path.basename(out), hashlib.sha256(open(out, "rb").read()).hexdigest())

app, w = dx.launch(exe, d)
w.set_focus()
w.menu_select("#0->#5")
dx.file_dialog(app, doc)
print("import:", dx.dismiss(app), w.window_text())
convert_and_export(app, w, os.path.join(d, "p25_unicode.brl"))
w.set_focus()
w.menu_select("#1->#4")
time.sleep(2)
s = app.window(handle=[h for h in app.windows(visible_only=True) if h.handle != w.handle][0].handle)
print("settings:", s.window_text())
combo = s.child_window(class_name="ComboBox", found_index=0).wrapper_object()
print("modes:", combo.texts())
combo.select("ASCII")
s.child_window(title="確定", class_name="Button").wrapper_object().click()
time.sleep(1.5)
convert_and_export(app, w, os.path.join(d, "p25_ascii.brl"))
print("config:", open(os.path.join(d, "config.json"), encoding="utf-8").read())
w.close()
time.sleep(2)
print("dialogs after close:", dx.dismiss(app) if app.is_process_running() else "process exited")
