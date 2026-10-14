"""Run an F-13 GUI script so that no key can reach another program (F-12's safe_run.py, adapted).

Usage: python safe_run.py <script.py> <exe> <work folder> [more arguments]

Every pywinauto ``send_keys`` first checks that the foreground window belongs to a process
whose exe lies under <work folder>; if it does not within 5 s, it raises instead of sending.
``f5gui.describe`` reports the focus as "<another program>" when the foreground window is not
the app's, so the logs never hold another program's element name. F-13: the old start
helpers (f8agui.start, f8bgui.start, dx.launch) are replaced by f13gui's, which wait until
the workspace is loaded (spec D2), so that the scripts of earlier items run unchanged; the
script may live in another history folder. The script runs with runpy, with
sys.argv = [script, exe, work folder, ...].
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
import f13gui  # noqa: E402

f13gui.FOLDER = FOLDER


def safe_send_keys(*args, **kwargs):
	end = time.time() + 5
	while not f13gui.foreground_is_app():
		if time.time() > end:
			raise RuntimeError("the foreground window is not the app under test; no key was sent")
		time.sleep(0.2)
	return _send_keys(*args, **kwargs)


keyboard.send_keys = safe_send_keys
_describe = f13gui.F.describe


def safe_describe(dialog):
	described = _describe(dialog)
	if not f13gui.foreground_is_app():
		described["focus"] = "<another program>"
	return described


f13gui.F.describe = safe_describe
sys.path.insert(0, os.path.join(f13gui.HISTORY, "2026-10-11-01-f11-dictionary-editor-ux", "auto"))
import f11gui  # noqa: E402  (the dictionary editor helpers; its focus is masked as F-11's safe_run did)

_focused = f11gui.focused


def safe_focused():
	if not f13gui.foreground_is_app():
		return ("<another program>", "")
	return _focused()


f11gui.focused = safe_focused
f13gui.install()
sys.path.insert(0, os.path.dirname(SCRIPT))
sys.argv = [SCRIPT] + sys.argv[2:]
runpy.run_path(SCRIPT, run_name="__main__")
