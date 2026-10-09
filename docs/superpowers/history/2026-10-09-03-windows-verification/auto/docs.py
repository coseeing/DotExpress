import os, time, hashlib, stat
import dx

def ws_state(d):
	ws = os.path.join(d, "workspace")
	out = {}
	for n in sorted(os.listdir(ws)):
		p = os.path.join(ws, n)
		a = os.stat(p).st_file_attributes
		flags = "".join(f for f, bit in (("R", stat.FILE_ATTRIBUTE_READONLY), ("H", stat.FILE_ATTRIBUTE_HIDDEN)) if a & bit)
		out[n] = (content_hash(p), flags)
	return out

def content_hash(p):
	import zipfile
	h = hashlib.sha256()
	try:
		with zipfile.ZipFile(p) as z:
			for i in z.infolist():
				h.update(i.filename.encode() + b"|" + z.read(i) + b"|")
		return "zip:" + h.hexdigest()[:10]
	except Exception:
		return "raw:" + hashlib.sha256(open(p, "rb").read()).hexdigest()[:10]

def docs(w):
	lv = w.child_window(class_name="SysListView32").wrapper_object()
	return [lv.get_item(i).text() for i in range(lv.item_count())]

def select(w, name):
	lv = w.child_window(class_name="SysListView32").wrapper_object()
	for i in range(lv.item_count()):
		if lv.get_item(i).text() == name:
			lv.get_item(i).select()
			time.sleep(0.8)
			return
	raise KeyError(name)

def has_edit(win):
	return any(c.class_name() == "Edit" for c in win.wrapper_object().descendants())

def name_dialog(app, w, menu, name):
	w.set_focus()
	w.menu_select(menu)
	pre = []
	end = time.time() + 15
	dlg = None
	while time.time() < end:
		time.sleep(0.6)
		for h in app.windows(visible_only=True):
			if h.handle == w.handle:
				continue
			win = app.window(handle=h.handle)
			if has_edit(win):
				dlg = win
			else:
				pre += dx.dismiss(app)
		if dlg is not None:
			break
	if dlg is None:
		return None, pre, "no name dialog"
	title = dlg.window_text()
	dlg.child_window(class_name="Edit").wrapper_object().set_edit_text(name)
	[c for c in dlg.wrapper_object().descendants() if c.class_name() == "Button" and c.window_text() in ("確定", "OK")][0].click()
	time.sleep(1.2)
	msgs = dx.dismiss(app)
	left = [h.window_text() for h in app.windows(visible_only=True) if h.handle != w.handle]
	return title, pre, msgs, left

def cancel_open(app, w):
	time.sleep(0.5)
	for h in app.windows(visible_only=True):
		if h.handle != w.handle:
			win = app.window(handle=h.handle)
			bs = [c for c in win.wrapper_object().descendants() if c.class_name() == "Button" and c.window_text() in ("取消", "Cancel")]
			print("   cancel", repr(h.window_text()), [b.window_text() for b in bs], "buttons:", [c.window_text() for c in win.wrapper_object().descendants() if c.class_name() == "Button"])
			for b in bs:
				b.click()
				time.sleep(0.8)

def diff(a, b):
	return {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}

def add(app, w, name):
	return name_dialog(app, w, "#0->#3", name)

def rename(app, w, name):
	return name_dialog(app, w, "#0->#4", name)

def set_input(w, text):
	w.children(class_name="Edit")[0].set_edit_text(text)
	time.sleep(0.5)

def get_input(w):
	return w.children(class_name="Edit")[0].window_text()

def close(app, w, timeout=15):
	import win32con
	w.post_message(win32con.WM_CLOSE)
	msgs = []
	end = time.time() + timeout
	while time.time() < end:
		time.sleep(0.8)
		if not app.is_process_running():
			return msgs or "exited"
		msgs += dx.dismiss(app)
	dx.kill_under(os.path.dirname(app.process and __import__("psutil").Process(app.process).exe()))
	return msgs + ["STILL RUNNING -> killed"]
