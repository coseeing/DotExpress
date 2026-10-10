"""Run an earlier GUI script against the F-5 build, closing message boxes through UIA (F-5).

Usage: python rerun.py <script.py> <exe> <work folder> [--seed <folder>]

item18.py, item19.py and item21.py of 2026-10-09-03 hard-code the N build and
D:\\dxtest\\auto18: those two literals are replaced in memory (each must occur once), as
F-3's rerun.py does. Any other script (item20b.py of 2026-10-09-03, item33.py of F-3)
gets <exe> and <work folder> as its arguments. With --seed, the work folder (which must
not exist yet) starts as a copy of the given folder.

The scripts run unchanged, with __file__ pointing at the original, except that
dx.dismiss is replaced by f5gui.dismiss for the run: the wx message boxes are task
dialogs, and the win32 click of dx.dismiss does not close them (seen in the F-5 dry run;
an open box keeps the process alive after Close). The committed scripts are not changed.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f5gui  # noqa: E402

OLD_EXE = 'r"D:\\dxtest\\N\\DotExpress.exe"'
OLD_DIR = 'r"D:\\dxtest\\auto18"'


def main():
	args = sys.argv[1:]
	seed = None
	if "--seed" in args:
		index = args.index("--seed")
		seed = args[index + 1]
		del args[index:index + 2]
	script, exe, work = (os.path.abspath(arg) for arg in args)
	with open(script, encoding="utf-8") as handle:
		source = handle.read()
	if OLD_EXE in source or OLD_DIR in source:
		for old in (OLD_EXE, OLD_DIR):
			if source.count(old) != 1:
				sys.exit(f"{old} occurs {source.count(old)} times in {script}")
		source = source.replace(OLD_EXE, repr(exe)).replace(OLD_DIR, repr(work))
		sys.argv = [script]
	else:
		sys.argv = [script, exe, work]
	if seed is not None:
		if os.path.exists(work):
			sys.exit(f"{work} exists; --seed needs a new folder")
		shutil.copytree(seed, work)
	f5gui.dx.dismiss = f5gui.dismiss
	sys.path.insert(0, os.path.dirname(script))
	exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
	main()
