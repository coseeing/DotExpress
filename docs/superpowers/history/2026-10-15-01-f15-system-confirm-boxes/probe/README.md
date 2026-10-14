# F-15 probe: the confirm boxes without access keys (2026-10-15)

Question: if the two F-11 confirm boxes of the dictionary editor ("移除無法顯示的列" and "尚未儲存的變更") become system Yes/No boxes (`wx.MessageDialog` + `SetYesNoLabels`) whose labels have **no** access keys, can any Alt+key, Esc or the close button answer "移除並儲存" or "放棄變更"?

**Result: no. Of 35 actions per box, only Enter answers, with the default "返回編輯" (ID_NO). The other 34 do nothing.** F-15 makes `ui.message_box.confirm_box` this box.

## Setup

- Run by the orchestrator on 2026-10-15 with the same machine and tools as the F-13 probe: wx 4.2.5 msw (phoenix), wxWidgets 3.2.9, the client venv's Python 3.13, Windows 11 Pro 10.0.26200, zh-TW; pywinauto 0.6.9 + psutil in a separate venv. The probe runs on its own and does not use `gui.py`.
- The scripts wrap the committed F-13 probe in `../../2026-10-14-02-f13-behavior-nvda/probe/` (see its `README.md`) and import it through a `sys.path` entry relative to this folder:
  - `box15.py` adds two variants to `probe_box.py`: `remove_nokey` (Yes = 移除並儲存, No = 返回編輯) and `discard_nokey` (Yes = 放棄變更, No = 返回編輯), both `wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING` with the F-11 captions and messages. As in F-13, the box is raised from a modal `wx.Dialog`, the way `DictionaryEntriesDialog._on_ok` and `_on_cancel` raise theirs.
  - `drive15.py` points `drive_probe.py` at `box15.py` and gives it 35 actions: Esc, Enter, the close button, Alt+F1 to Alt+F12, Alt+Numpad0 to Alt+Numpad9, Alt with the numpad keys `*`, `+`, separator, `-`, `.` and `/`, and Alt+S, Alt+D, Alt+B, Alt+Y. Each action starts a fresh probe process. Keys go out with pywinauto `send_keys`; "close" clicks with the mouse. The scripts do not use the clipboard.
- Usage, as for F-13: `python drive15.py <client venv python.exe> <work folder> remove_nokey discard_nokey`.
- Raw output: `sweep.jsonl`, one JSON line per variant and action (70 lines). It is valid UTF-8; the button names in its `buttons` field are readable, not mojibake.

## Results

Both boxes are `#32770` windows owned by the probe editor, with no system menu and no close button: "close" clicks the top-right corner of the title bar, which hits `HTCAPTION` (2). The buttons show their labels as given, with no access key added by Windows. The focus starts on 返回編輯.

| Variant | Buttons (focus) | Enter | The other 34 actions |
| --- | --- | --- | --- |
| `remove_nokey` | 移除並儲存, 返回編輯 (返回編輯) | ID_NO = back to editing | nothing (the box stays open) |
| `discard_nokey` | 放棄變更, 返回編輯 (返回編輯) | ID_NO = back to editing | nothing (the box stays open) |

## Explanation

The F-13 probe found the rule: in a native task dialog, Alt+<key> presses the button whose access-key character code equals the key's virtual-key code (Alt+F4 is `s`, Alt+F10 is `y`, Alt+Numpad4 is `d`). Every letter has such a key, so a button with an access key can always be pressed by some Alt+key. Without access keys, no Alt+key has a button to press, which this sweep confirms for every key that maps to a letter (Numpad0-9 and the numpad operators cover `` ` `` and a-o, F1-F12 cover p-{) and for the letter keys themselves.

Esc, Alt+F4 and the close button do nothing in these boxes; the user accepted that on 2026-10-15. F-11's `wx.GenericMessageDialog` answered them with Cancel, but it is not the system box the other confirmations use.
