r"""Prepare the folder of the manual NVDA items 159 and 160 (F-18); the app is not started.

Usage: <uia python> manual159.py <exe> <folder under D:\dxtest>
The folder gets the exe, the pending document alpha, script\upper.py (valid),
script\broken.py (a syntax error, so that the reason field shows) and script\cp950.py (not
UTF-8: 無法讀取). config.json selects no script (No Processing). Nothing is started and no
key is sent.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import F9  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
if not os.path.normcase(d).startswith(os.path.normcase("D:\\dxtest\\manual")):
	sys.exit(f"refusing {d}: not under D:\\dxtest\\manual*")
if os.path.exists(d):
	sys.exit(f"{d} exists already")
os.makedirs(os.path.join(d, "workspace"))
shutil.copy(EXE, os.path.join(d, "DotExpress.exe"))
F9.pending(d, "alpha", "abc 臺灣")
H.script(d, "upper", H.UPPER)
H.script(d, "broken", b"def main(text)\n    return text\n")
H.script(d, "cp950", "def main(text):\n    return text + '臺'\n".encode("cp950"))
print("prepared:", sorted(os.listdir(d)), sorted(os.listdir(os.path.join(d, "script"))))
