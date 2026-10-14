"""Drive probe_box.py (F-13 item 5 precondition) with pywinauto 0.6.9 + psutil.

Usage: python drive_probe.py <client venv python.exe> <work folder> [variant | variant:action ...]

For each variant (default: remove discard swapped system) and each action (esc,
alt-f4, close, enter) it starts a fresh probe process, waits for the box, reads it
through UIA (buttons, focus, owner, title-bar close button), brings it to the
foreground and does the action: a key through pywinauto send_keys, or for "close" a
real mouse click on the box's title-bar close button. Keys and the click are sent
only while the foreground window belongs to the probe process (else the run stops
without sending anything). After 3 s the result is the answer the probe wrote, or
"nothing happened" if the box is still open. Only the probe's own processes are
killed. Names of other programs' windows are never read or logged. The clipboard is
not used.
"""
import ctypes
import json
import os
import subprocess
import sys
import time

import psutil
import win32con
import win32gui
import win32process
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "probe_box.py")
CAPTIONS = {"discard": "尚未儲存的變更"}  # every other variant: 移除無法顯示的列
KEYS = {"esc": "{ESC}", "alt-f4": "%{F4}", "enter": "{ENTER}", "alt-num4": "%{VK_NUMPAD4}", "alt-num2": "%{VK_NUMPAD2}", "alt-f10": "%{F10}"}
ACTIONS = ("esc", "alt-f4", "close", "enter")


def tree(pid):
	"""The pid of the started process and of its children (the venv launcher starts one)."""
	pids = {pid}
	try:
		pids.update(child.pid for child in psutil.Process(pid).children(recursive=True))
	except psutil.Error:
		pass
	return pids


def window_pid(handle):
	return win32process.GetWindowThreadProcessId(handle)[1]


def find_box(pids, caption, timeout=20):
	end = time.time() + timeout
	while time.time() < end:
		found = []

		def collect(handle, _):
			if win32gui.IsWindowVisible(handle) and window_pid(handle) in pids:
				if win32gui.GetWindowText(handle) == caption:
					found.append(handle)
			return True

		win32gui.EnumWindows(collect, None)
		if found:
			return found[0]
		time.sleep(0.3)
		pids = pids | tree(min(pids))
	return None


def foreground_is_probe(pids):
	handle = win32gui.GetForegroundWindow()
	return bool(handle) and window_pid(handle) in pids


def bring_to_front(box, pids):
	for _ in range(10):
		try:
			box.set_focus()
		except Exception:
			pass
		time.sleep(0.3)
		if foreground_is_probe(pids):
			return True
	return False


def describe(handle, pids):
	box = Desktop(backend="uia").window(handle=handle)
	buttons = []
	close_button = None
	for button in box.descendants(control_type="Button"):
		name = button.window_text()
		automation_id = button.element_info.automation_id
		if automation_id == "Close":
			close_button = button
			continue
		buttons.append(name)
	focus = None
	if foreground_is_probe(pids):
		focused = [b.window_text() for b in box.descendants(control_type="Button") if b.has_keyboard_focus()]
		focus = focused[0] if focused else None
	owner = win32gui.GetWindow(handle, win32con.GW_OWNER)
	style = win32gui.GetWindowLong(handle, win32con.GWL_STYLE)
	return {
		"class": win32gui.GetClassName(handle),
		"buttons": buttons,
		"focus": focus,
		"owner": win32gui.GetWindowText(owner) if owner and window_pid(owner) in pids else owner,
		"sysmenu": bool(style & win32con.WS_SYSMENU),
		"close button": close_button is not None,
	}, box, close_button


def hit_test(handle, x, y):
	return ctypes.windll.user32.SendMessageW(handle, win32con.WM_NCHITTEST, 0, (y << 16) | (x & 0xFFFF))


def run(python, work, variant, action):
	result_path = os.path.join(work, f"{variant}-{action}.json")
	if os.path.exists(result_path):
		os.remove(result_path)
	process = subprocess.Popen([python, "-B", PROBE, variant, result_path], cwd=work)
	pids = tree(process.pid)
	record = {"variant": variant, "action": action}
	try:
		handle = find_box(pids, CAPTIONS.get(variant, "移除無法顯示的列"))
		pids = tree(process.pid)
		if handle is None:
			record["error"] = "no box"
			return record
		if not bring_to_front(Desktop(backend="uia").window(handle=handle), pids):
			record["error"] = "the box did not come to the foreground; nothing sent"
			return record
		record["box"], box, close_button = describe(handle, pids)
		if not foreground_is_probe(pids):
			record["error"] = "the foreground changed; nothing sent"
			return record
		if action == "close":
			if close_button is not None:
				close_button.click_input()
				record["did"] = "clicked the title-bar close button"
			else:
				left, top, right, _bottom = win32gui.GetWindowRect(handle)
				x, y = right - 20, top + 15
				record["did"] = f"no close button; clicked the top-right corner of the title bar, hit test {hit_test(handle, x, y)}"
				import pywinauto.mouse as mouse

				mouse.click(coords=(x, y))
		else:
			send_keys(KEYS[action])
			record["did"] = f"sent {action}"
		end = time.time() + 3
		while time.time() < end and process.poll() is None:
			time.sleep(0.2)
		if os.path.exists(result_path):
			with open(result_path, encoding="utf-8") as stream:
				record["result"] = json.load(stream)
		elif win32gui.IsWindow(handle) and win32gui.IsWindowVisible(handle):
			record["result"] = "nothing happened (the box is still open)"
		else:
			record["result"] = f"box gone, no answer written, exit code {process.poll()}"
		return record
	finally:
		for pid in tree(process.pid) | pids:
			try:
				psutil.Process(pid).kill()
			except psutil.Error:
				pass


def main():
	python, work = sys.argv[1], sys.argv[2]
	runs = []
	for argument in sys.argv[3:] or ["remove", "discard", "swapped", "system"]:
		variant, _, action = argument.partition(":")
		runs.extend([(variant, action)] if action else [(variant, each) for each in ACTIONS])
	os.makedirs(work, exist_ok=True)
	for variant, action in runs:
		record = run(python, work, variant, action)
		print(json.dumps(record, ensure_ascii=False), flush=True)
		time.sleep(1)


if __name__ == "__main__":
	main()
