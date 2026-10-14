r"""Item 142 (F-14 D7): the box of a failed settings backup.

Usage: python safe_run.py item142.py <exe> <work folder>
Runs F-12's item114.py, case (b), unchanged: config.json holds "{" and config.json.bak is a
folder; Settings: change the width, Apply, then OK; each box (title, main instruction,
content, owner) and config.json. Then prints the ERROR messages of log\config.log and
whether its traceback holds WinError 5 (the log keeps the operating system's text).
Before F-14 (N-f12b): the content ends with 詳細資訊：[WinError 5] ... .tmp' -> ...
"""
import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f14gui as H  # noqa: E402

ITEM114 = os.path.join(H.HISTORY, "2026-10-11-02-f12-localization-cleanup", "auto", "item114.py")
EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
sys.argv = [ITEM114, EXE, d, "b"]
runpy.run_path(ITEM114, run_name="__main__")
print("142 config.log:", H.config_log(d))
