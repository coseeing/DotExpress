r"""Item 129 (F-13 D6): the removal list shows the Bopomofo value as it is in the file.

Usage: python safe_run.py item129.py <exe> <work folder>
dictionary\raw.csv (UTF-8, CRLF): text,braille,type / 抹,ㄇㄚ + two spaces,Bopomofo /
媽,space + ㄇㄚ,Bopomofo / 甲乙,⠁⠃,Braille. Open it in the dictionary editor, press OK (with
BM_CLICK): the box, read through UIA (its lines of text); Alt+B (返回編輯): the editor stays
and the file is unchanged; OK again, Alt+S (移除並儲存): the file.
Before F-13 (N-f12b): both lines show 「ㄇㄚ」.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f13gui as H  # noqa: E402
import f11gui as E  # noqa: E402  (safe_run.py puts F-11's auto folder on sys.path)

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
RAW = "text,braille,type\r\n抹,ㄇㄚ  ,Bopomofo\r\n媽, ㄇㄚ,Bopomofo\r\n甲乙,⠁⠃,Braille\r\n".encode("utf-8")
app, w = E.setup(EXE, d, {"raw.csv": RAW})
path = E.dictionary(d, "raw")
before = E.state(path)
ed = E.editor(app, w, "raw")
print("129 rows:", E.X.editor_rows(ed))
E.press_button(ed, "確定")
print("129 box:", E.next_box(app, "alt-b"))
print("129 back to editing: windows", E.windows(app, w), "file", E.same(before, path), "focus", E.focused())
ed = E.X.windows(app, w).get(E.EDITOR) or E.editor(app, w, "raw")
E.press_button(ed, "確定")
print("129 Alt+S: box", E.next_box(app, "alt-s"))
print("129 Alt+S: windows", E.windows(app, w), "file", repr(E.text(path)))
E.finish(app, w, d)
