"""Shared helpers for the F-3 GUI checks (pywinauto 0.6.9 + psutil; Windows, zh-TW UI).

Reuses dx.py, docs.py and lock.py of the 2026-10-09-03 Windows verification unchanged.
Every item script takes <exe> <work folder>; dx.launch deletes the folder first.
"""
import os
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO03 = os.path.normpath(os.path.join(HERE, "..", "..", "2026-10-09-03-windows-verification", "auto"))
sys.path.insert(0, AUTO03)
import dx  # noqa: E402
import docs as D  # noqa: E402

LOCK = os.path.join(AUTO03, "lock.py")


def workspace(d):
    return os.path.join(d, "workspace")


def files(d):
    return sorted(os.listdir(workspace(d)))


def leftovers(d):
    return [name for name in files(d) if name.endswith(".tmp")]


def open_document(app, w, name):
    """Select ``name``, choose File > Open (#0->#0) and return the message boxes it showed."""
    D.select(w, name)
    w.set_focus()
    w.menu_select("#0->#0")
    time.sleep(1.2)
    return dx.dismiss(app)


def setup_alpha_beta(exe, d):
    """A new work folder with the documents alpha ("alpha body") and beta ("beta body"); alpha is open."""
    app, w = dx.launch(exe, d)
    print("add alpha:", D.add(app, w, "alpha"))
    D.set_input(w, "alpha body")
    print("add beta:", D.add(app, w, "beta"))
    D.set_input(w, "beta body")
    print("open alpha:", open_document(app, w, "alpha"))
    print("docs:", D.docs(w), "title:", w.window_text(), "files:", files(d))
    return app, w


def attrib(path):
    return subprocess.run(["cmd", "/c", "attrib", path], capture_output=True, text=True).stdout.strip()


def member_text(path, member):
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
