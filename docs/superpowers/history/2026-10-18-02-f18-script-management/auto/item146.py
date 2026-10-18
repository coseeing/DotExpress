r"""Items 146 (F-18 D1, D3, D11) and 148 (D7): a first start, the menu, Settings, Script Management.

Usage: python safe_run.py item146.py <exe> <work folder>
A new folder with the pending document alpha. 146: the script folder after the start
(no-processing.py and its bytes), the Translation menu, Settings > Translation (labels and
choices; closed with 取消), config.json. 148: Script Management with 「不處理」 selected:
the rows, the selected row, the buttons, the reason field, the focus; closed with 關閉.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f18gui as H  # noqa: E402
from f18gui import D, F9  # noqa: E402

EXE, d = sys.argv[1], os.path.normpath(sys.argv[2])
d = H.prepare(EXE, d)
F9.pending(d, "alpha", "abc")
app, w, shown = H.start(d)
print(f"146 start: shown {shown} docs {D.docs(w)}")
files = H.script_files(d)
print("146 script folder:", sorted(files) if files is not None else None)
print("146 no-processing.py is the documented text:", files and files.get("no-processing.py") == H.NO_PROCESSING)
print("146 translation menu:", H.translation_menu(w))
dialog = H.settings(app, w)
print("146 settings:", H.translation_panel(dialog))
H.press(dialog, "取消", "Cancel")
print("146 config.json conversion:", H.config(d))
mgr = H.open_manager(app, w)
print("148 rows:", H.rows(mgr))
print("148 selected:", H.selected_row(mgr))
print("148 buttons:", H.buttons(mgr))
print("148 reason:", H.reason(mgr))
print("148 focus:", H.focus())
H.press(mgr, "關閉", "Close")
print("148 windows after 關閉:", H.windows(app, w))
H.close(app, w, d)
