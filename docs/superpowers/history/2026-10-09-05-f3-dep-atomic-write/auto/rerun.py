"""Run a 2026-10-09-03 GUI script against another build and work folder (F-3).

Usage: python rerun.py <script.py> <exe> <work folder> [--seed <folder>]

item18.py, item19.py and item21.py hard-code the N build and D:\\dxtest\\auto18. This
wrapper reads the script, replaces exactly those two literals (each must occur once), and
runs it with __file__ pointing at the original, so it still imports dx/docs and finds
lock.py next to it. The committed scripts are not changed. With --seed, the work folder
(which must not exist yet) starts as a copy of the given folder: items 19 and 21 continue
from the documents item 18 leaves.
"""
import os
import shutil
import sys

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
    for old in (OLD_EXE, OLD_DIR):
        if source.count(old) != 1:
            sys.exit(f"{old} occurs {source.count(old)} times in {script}")
    source = source.replace(OLD_EXE, repr(exe)).replace(OLD_DIR, repr(work))
    if seed is not None:
        if os.path.exists(work):
            sys.exit(f"{work} exists; --seed needs a new folder")
        shutil.copytree(seed, work)
    sys.argv = [script]
    sys.path.insert(0, os.path.dirname(script))
    exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})


if __name__ == "__main__":
    main()
