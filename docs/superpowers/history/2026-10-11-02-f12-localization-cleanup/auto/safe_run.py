"""Run an F-12 GUI script so that no key can reach another program (F-11's safe_run.py, adapted).

Usage: python safe_run.py <script.py> <exe> <work folder> [more arguments]

Every pywinauto ``send_keys`` (the scripts and the helpers they reuse import it when they
press a key) first checks that the foreground window belongs to a process whose exe lies
under <work folder>; if it does not within 5 s, it raises instead of sending. f5gui.answer
sends after ten failed attempts to bring the box to the foreground; with this wrapper it
stops the script instead. ``f5gui.describe`` reports the focus as "<another program>" when
the foreground window is not the app's, so the logs never hold another program's element
name. The script runs unchanged with runpy, with sys.argv = [script, exe, work folder, ...].
"""
import os
import runpy
import sys
import time

import psutil
import pywinauto.keyboard as keyboard
import win32gui
import win32process

SCRIPT = os.path.abspath(sys.argv[1])
FOLDER = os.path.normcase(os.path.normpath(sys.argv[3]))
_send_keys = keyboard.send_keys


def foreground_is_app():
	"""Whether the foreground window belongs to a process whose exe lies under FOLDER."""
	handle = win32gui.GetForegroundWindow()
	if not handle:
		return False
	pid = win32process.GetWindowThreadProcessId(handle)[1]
	try:
		exe = psutil.Process(pid).exe()
	except psutil.Error:
		return False
	return os.path.normcase(exe).startswith(FOLDER + os.sep)


def safe_send_keys(*args, **kwargs):
	end = time.time() + 5
	while not foreground_is_app():
		if time.time() > end:
			raise RuntimeError("the foreground window is not the app under test; no key was sent")
		time.sleep(0.2)
	return _send_keys(*args, **kwargs)


keyboard.send_keys = safe_send_keys
sys.path.insert(0, os.path.dirname(SCRIPT))
import f12gui  # noqa: E402  (the module object the scripts import as H)

_describe = f12gui.F.describe


def safe_describe(dialog):
	described = _describe(dialog)
	if not foreground_is_app():
		described["focus"] = "<another program>"
	return described


f12gui.F.describe = safe_describe
sys.argv = [SCRIPT] + sys.argv[2:]
runpy.run_path(SCRIPT, run_name="__main__")
