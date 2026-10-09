import os, time
import dx

def btn(win, *titles):
	for c in win.wrapper_object().descendants():
		if c.class_name() == "Button" and c.window_text() in titles:
			return c
	raise KeyError(titles)

def windows(app, w):
	return {h.window_text(): app.window(handle=h.handle) for h in app.windows(visible_only=True) if h.handle != w.handle}

def wait_window(app, w, title, timeout=10):
	end = time.time() + timeout
	while time.time() < end:
		ws = windows(app, w)
		if title in ws:
			return ws[title]
		time.sleep(0.3)
	raise RuntimeError(f"no window {title}: {list(windows(app, w))}")

def open_mgr(app, w):
	w.set_focus()
	w.menu_select("#1->#3")
	return wait_window(app, w, "字典管理")

def mgr_items(mgr):
	lv = [c for c in mgr.wrapper_object().descendants() if c.class_name() == "SysListView32"][0]
	return lv, [[lv.get_item(i, j).text() for j in range(lv.column_count())] for i in range(lv.item_count())]

def mgr_select(mgr, name):
	lv, items = mgr_items(mgr)
	for i, row in enumerate(items):
		if row[0] == name:
			lv.get_item(i).select()
			time.sleep(0.5)
			return
	raise KeyError((name, items))

def popups(app, w, keep=("字典管理",)):
	"""Read and dismiss TaskDialog-style popups (no edit field), leave named windows alone."""
	out = []
	for title, win in windows(app, w).items():
		if title in keep:
			continue
		texts = dx.dialog_text(win)
		if "檔案名稱:" in texts:
			continue
		descs = win.wrapper_object().descendants()
		if any(c.class_name() in ("Edit", "SysListView32") for c in descs):
			continue
		out.append((title, [t for t in texts if t not in ("MainInstructionIcon", "關閉", title)]))
		for c in descs:
			if c.class_name() == "Button" and c.window_text() in ("OK", "確定"):
				c.click()
				break
		time.sleep(0.6)
	return out

def import_dict(app, w, mgr, path):
	btn(mgr, "匯入").click()
	fd = wait_window(app, w, "匯入字典")
	fd.child_window(class_name="Edit", found_index=0).wrapper_object().set_edit_text(path)
	[c for c in fd.wrapper_object().descendants() if c.class_name() == "Button"][0].click()
	time.sleep(2)

def import_named(app, w, mgr, path):
	import_dict(app, w, mgr, path)
	nd = wait_window(app, w, "新增字典")
	btn(nd, "確定", "OK").click()
	time.sleep(1.5)
	return popups(app, w)

def editor_rows(ed):
	l = [c for c in ed.wrapper_object().descendants() if c.class_name() == "SysListView32"][0]
	return [[l.get_item(i, j).text() for j in range(l.column_count())] for i in range(l.item_count())]

def open_editor(app, w, mgr, name):
	mgr_select(mgr, name)
	btn(mgr, "編輯").click()
	return wait_window(app, w, "自訂字典管理器")

def editor_ok(app, w, ed, keep=("字典管理", "自訂字典管理器")):
	btn(ed, "確定", "OK").click()
	time.sleep(1.5)
	msgs = popups(app, w, keep=keep)
	still_open = "自訂字典管理器" in windows(app, w)
	return msgs, still_open

def close_mgr(app, w, mgr):
	btn(mgr, "關閉", "Close").click()
	time.sleep(1)

def set_dictionary(app, w, name):
	w.set_focus(); w.menu_select("#1->#4"); time.sleep(2)
	s = app.window(handle=[h for h in app.windows(visible_only=True) if h.handle != w.handle][0].handle)
	cb = [c for c in s.wrapper_object().descendants() if c.class_name() == "ComboBox"][1]
	cb.select(name)
	btn(s, "確定", "OK").click()
	time.sleep(1.2)

def convert(app, w):
	edits = w.children(class_name="Edit")
	w.set_focus(); w.menu_select("#1->#0")
	end = time.time() + 60
	while time.time() < end and not dx.dialogs(app):
		time.sleep(0.4)
	msgs = dx.dismiss(app)
	return edits[1].window_text(), msgs
