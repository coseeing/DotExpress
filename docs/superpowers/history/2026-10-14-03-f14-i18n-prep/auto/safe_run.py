"""Run an F-14 GUI script so that no key can reach another program (F-12's safe_run.py, adapted).

Usage: python safe_run.py <script.py> <exe> <work folder> [more arguments]

Every pywinauto ``send_keys`` first checks that the foreground window belongs to a process
whose exe lies under <work folder>; if it does not within 5 s, it raises instead of sending.
``f5gui.describe`` and ``f11gui.focused`` report the focus as "<another program>" when the
foreground window is not the app's, so the logs never hold another program's element name.
The script may live in another history folder (item 142 runs F-12's item114.py); it runs
with runpy, with sys.argv = [script, exe, work folder, ...].
"""
import os
import runpy
import sys
import time

import pywinauto.keyboard as keyboard

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(sys.argv[1])
FOLDER = os.path.normcase(os.path.normpath(sys.argv[3]))
_send_keys = keyboard.send_keys
sys.path.insert(0, HERE)
import f14gui  # noqa: E402

f14gui.FOLDER = FOLDER


def safe_send_keys(*args, **kwargs):
	end = time.time() + 5
	while not f14gui.foreground_is_app():
		if time.time() > end:
			raise RuntimeError("the foreground window is not the app under test; no key was sent")
		time.sleep(0.2)
	return _send_keys(*args, **kwargs)


keyboard.send_keys = safe_send_keys
_describe = f14gui.F.describe


def safe_describe(dialog):
	described = _describe(dialog)
	if not f14gui.foreground_is_app():
		described["focus"] = "<another program>"
	return described


f14gui.F.describe = safe_describe
_focused = f14gui.H11.focused


def safe_focused():
	if not f14gui.foreground_is_app():
		return ("<another program>", "")
	return _focused()


f14gui.H11.focused = safe_focused
if os.environ.get("F14_START") == "f13":
	# A build that contains F-13 (N-f14b) shows its main window before the workspace is
	# loaded: F-13's start helpers wait for the load (run_item.sh sets F14_START).
	sys.path.insert(0, os.path.join(f14gui.HISTORY, "2026-10-14-02-f13-behavior-nvda", "auto"))
	import f13gui  # noqa: E402

	f13gui.FOLDER = FOLDER
	f13gui.install()
sys.path.insert(0, os.path.dirname(SCRIPT))
sys.argv = [SCRIPT] + sys.argv[2:]
runpy.run_path(SCRIPT, run_name="__main__")
