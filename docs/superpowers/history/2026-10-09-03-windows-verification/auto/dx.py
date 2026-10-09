import os, shutil, subprocess, time
from pywinauto import Application, Desktop
from pywinauto.findwindows import find_windows

def kill_under(prefix):
	prefix = os.path.normpath(prefix)
	subprocess.run(["powershell", "-NoProfile", "-Command",
		f"Get-Process DotExpress -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '{prefix}*' }} | Stop-Process -Force"])
	time.sleep(1.5)

def launch(exe, d, fresh=True):
	d = os.path.normpath(d)
	if fresh and os.path.isdir(d):
		kill_under(d)
		shutil.rmtree(d)
	os.makedirs(d, exist_ok=True)
	target = os.path.join(d, "DotExpress.exe")
	if not os.path.exists(target):
		shutil.copy(exe, target)
	subprocess.Popen([target], cwd=d)
	return attach(d)

def attach(d, timeout=40):
	d = os.path.normpath(d)
	import psutil
	end = time.time() + timeout
	while time.time() < end:
		for p in psutil.process_iter(["name", "exe", "pid"]):
			if p.info["name"] == "DotExpress.exe" and (p.info["exe"] or "").lower().startswith(d.lower()):
				hs = find_windows(process=p.info["pid"], title_re=".*DotExpress$", visible_only=True)
				if hs:
					app = Application(backend="win32").connect(handle=hs[0])
					w = app.window(handle=hs[0])
					w.wait("visible", timeout=20)
					return app, w
		time.sleep(0.5)
	raise RuntimeError("main window not found")

def dump_menu(w):
	def dump(items, ind=0):
		for it in items:
			print("  " * ind + repr(it.text()), it.is_enabled())
			if it.sub_menu():
				dump(it.sub_menu().items(), ind + 1)
	dump(w.menu().items())

def file_dialog(app, path, title=None, wait=1.5):
	dlg = wait_dialog(app, wait)
	if title:
		assert dlg.window_text() == title, dlg.window_text()
	print("file dialog:", dlg.window_text())
	edit = dlg.child_window(class_name="Edit", found_index=0)
	edit.set_edit_text(path)
	dlg.child_window(class_name="Button", found_index=0).click()
	time.sleep(1.5)

def popup_report(app, main):
	time.sleep(1)
	top = app.top_window()
	if top.handle != main.handle:
		texts = [c.window_text() for c in top.children() if c.window_text()]
		print("popup:", top.window_text(), texts)
		return top
	return None

def wait_text(ctrl, timeout=120):
	end = time.time() + timeout
	last = None
	while time.time() < end:
		t = ctrl.window_text()
		if t and t == last:
			return t
		last = t
		time.sleep(1)
	return ctrl.window_text()

def wait_dialog(app, wait=0.5, timeout=20):
	time.sleep(wait)
	end = time.time() + timeout
	while time.time() < end:
		for win in app.windows(class_name="#32770", visible_only=True):
			return app.window(handle=win.handle)
		time.sleep(0.5)
	raise RuntimeError("no dialog")

def dialogs(app):
	return [app.window(handle=h.handle) for h in app.windows(class_name="#32770", visible_only=True)]

def dialog_text(dlg):
	from pywinauto import Desktop
	u = Desktop(backend="uia").window(handle=dlg.handle)
	seen = []
	for e in u.descendants():
		t = e.window_text()
		if t and t not in seen:
			seen.append(t)
	return seen

def dismiss(app, button_titles=("OK", "確定", "是(&Y)", "否(&N)")):
	out = []
	for dlg in dialogs(app):
		texts = dialog_text(dlg)
		if "檔案名稱:" in texts:
			out.append((dlg.window_text(), "<file dialog left open>"))
			continue
		out.append((dlg.window_text(), [t for t in texts if t not in ("MainInstructionIcon", "關閉")]))
		for t in button_titles:
			b = dlg.child_window(title=t, class_name="Button")
			if b.exists(timeout=0.2):
				b.wrapper_object().click()
				break
		time.sleep(0.8)
	return out

def other_window(app, main, timeout=10):
	end = time.time() + timeout
	while time.time() < end:
		hs = [h for h in app.windows(visible_only=True) if h.handle != main.handle]
		if hs:
			return app.window(handle=hs[0].handle)
		time.sleep(0.3)
	return None

def list_controls(win):
	for c in win.descendants():
		if c.is_visible():
			print(" ", c.class_name(), repr(c.window_text()), c.control_id())
