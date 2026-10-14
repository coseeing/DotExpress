r"""Manual item 131 (NVDA): write the workspace of item 125 into a folder for the user.

Usage: python manual131.py <exe> <folder>   (for example D:\dxtest\N-f13\DotExpress.exe D:\dxtest\manual131-f13)
The folder is emptied (only processes whose exe lies under it are ended) and gets a copy of
the exe and workspace\ with an invalid bad.dep, the interrupted Rename of alpha (to gamma)
whose text holds one U+0000, and a valid beta.dep. The app is not started: the user starts
<folder>\DotExpress.exe with NVDA on. A start recovers alpha, so run this again before
another try. Nothing here touches the clipboard.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f13gui as H  # noqa: E402
from f13gui import A, B  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = A.prepare(EXE, d)
A.write(os.path.join(d, "workspace", "bad.dep"), b"not a zip")
B.leftover(d, ".alpha.dep._vw4x6f_.tmp", "alpha", "alpha\x00body", "⠁", age_s=3600)
B.leftover(d, ".gamma.dep.mlw4jang.tmp", "gamma", "alpha\x00body", "⠁")
A.package(d, "beta", "beta body", "⠃")
print(f"manual 131 folder ready: {d} files {A.files(d)}")
