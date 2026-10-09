"""Run a 2026-10-09-03 dictionary GUI script against the F-4 build (F-4).

Usage: python rerun.py <item23.py|item24.py|item25.py|item29.py> [--check]

The committed scripts hard-code the N build (D:\\dxtest\\N\\DotExpress.exe) and their
work folders. This wrapper reads the script, replaces the literals listed in REPLACE
(each must occur exactly once) and runs it with __file__ pointing at the original, so it
still imports dx/docs/dicts and finds lock.py next to it. The committed scripts are not
changed.

- item23.py: B and the F-4 build (N-f4), in D:\\dxtest\\auto23-f4-B and
  D:\\dxtest\\auto23-f4-N-f4 (dx.launch deletes a work folder first).
- item24.py: the F-4 build in D:\\dxtest\\auto24-f4.
- item25.py: restarts the app in that folder and runs only up to "# 29 ACL deny write"
  (that section uses (W), superseded by item29.py, F-W13); the app stays open.
- item29.py: attaches to the app running in D:\\dxtest\\auto24-f4.

With --check nothing runs: each replaced line and the last line kept are printed.
"""
import os
import sys

N_EXE = 'r"D:\\dxtest\\N\\DotExpress.exe"'
F4_EXE = 'r"D:\\dxtest\\N-f4\\DotExpress.exe"'
AUTO24 = 'r"D:\\dxtest\\auto24"'
AUTO24_F4 = 'r"D:\\dxtest\\auto24-f4"'
REPLACE = {
	"item23.py": (
		('for v in ("B", "N"):', 'for v in ("B", "N-f4"):'),
		('rf"D:\\dxtest\\auto23-{v}"', 'rf"D:\\dxtest\\auto23-f4-{v}"'),
	),
	"item24.py": ((N_EXE, F4_EXE), (AUTO24, AUTO24_F4)),
	"item25.py": ((N_EXE, F4_EXE), (AUTO24, AUTO24_F4)),
	"item29.py": ((AUTO24, AUTO24_F4),),
}
STOP = {"item25.py": "# 29 ACL deny write\n"}


def main():
	args = sys.argv[1:]
	check = "--check" in args
	if check:
		args.remove("--check")
	script = os.path.abspath(args[0])
	name = os.path.basename(script)
	if name not in REPLACE:
		sys.exit(f"{name}: expected one of {sorted(REPLACE)}")
	with open(script, encoding="utf-8") as handle:
		source = handle.read()
	for old, new in REPLACE[name]:
		if source.count(old) != 1:
			sys.exit(f"{old} occurs {source.count(old)} times in {script}")
		source = source.replace(old, new)
	if name in STOP:
		if source.count(STOP[name]) != 1:
			sys.exit(f"{STOP[name]!r} occurs {source.count(STOP[name])} times in {script}")
		source = source[:source.index(STOP[name])]
	if check:
		for _old, new in REPLACE[name]:
			print(name, "|", next(line.strip() for line in source.splitlines() if new in line))
		print(name, "| last:", source.rstrip().splitlines()[-1].strip())
		return
	sys.argv = [script]
	sys.path.insert(0, os.path.dirname(script))
	exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
	main()
