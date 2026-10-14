# F-13 item 5 precondition probe (2026-10-14)

Question (HANDOFF section 4, `task.md` "下一輪要修" item 5): if the two F-11 confirmation boxes became system Yes/No boxes with custom labels (`wx.MessageDialog` + `SetYesNoLabels`), raised from the dictionary editor (a modal `wx.Dialog`), could Esc, Alt+F4 or the title-bar close button answer "移除並儲存" or "放棄變更"?

**Result: yes. Alt+F4 answers "移除並儲存(&S)". The precondition fails, so item 5 is dropped (spec D5).**

## Setup

- wx 4.2.5 msw (phoenix), wxWidgets 3.2.9, Python 3.13.15 (the client venv), Windows 11 Pro 10.0.26200, zh-TW. The probe runs on its own and does not use `gui.py`.
- `probe_box.py`: a frame owns a `wx.Dialog` shown with `ShowModal`. A button event posted to the dialog's OK button runs a handler that raises the box with the dialog as its parent. This is how `DictionaryEntriesDialog._on_ok` and `_on_cancel` raise theirs. The box uses `wx.MessageDialog(parent, message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)` with `SetYesNoLabels` and the zh_TW labels of the F-11 boxes. It writes the `ShowModal` answer to a JSON file.
- `drive_probe.py` (pywinauto 0.6.9 + psutil, venv in the session scratchpad): every run starts a fresh probe process and reads the box through UIA. Keys go out with `send_keys` only while the probe's window is in the foreground. For "close", the driver clicks the title-bar close button with the mouse; when the box has none, it clicks the top-right corner of the title bar. Only the probe's own processes were killed, the logs name no window of another program, and the clipboard was not used.
- Raw output: `probe-output.jsonl` (four variants x Esc / Alt+F4 / close / Enter), `probe-output-2.jsonl` (follow-up runs), `probe-output-3.jsonl` (Alt+F10 on the system box).

## Results

Every box is a `#32770` window owned by the probe editor. It has no system menu and no close button: the click at the title-bar corner hits `HTCAPTION` (2) and does nothing. The focus starts on the default button.

| Variant | Buttons (focus) | Esc | Alt+F4 | Close button | Enter |
| --- | --- | --- | --- | --- | --- |
| `remove`: Yes = 移除並儲存(&S), No = 返回編輯(&B), NO_DEFAULT | 移除並儲存(S), 返回編輯(B) (返回編輯) | nothing | **ID_YES = remove and save** (twice, in two separate runs) | none; nothing | ID_NO |
| `discard`: Yes = 放棄變更(&D), No = 返回編輯(&B), NO_DEFAULT | 放棄變更(D), 返回編輯(B) (返回編輯) | nothing | nothing (twice) | none; nothing | ID_NO |
| `swapped`: Yes = 返回編輯(&B), No = 移除並儲存(&S), YES_DEFAULT | 返回編輯(B), 移除並儲存(S) (返回編輯) | nothing | **ID_NO = remove and save** | none; nothing | ID_YES |
| `system`: system labels, NO_DEFAULT (like the existing four boxes) | 是(Y), 否(N) (否) | nothing | nothing | none; nothing | ID_NO |
| `remove_r`: as `remove`, access key R instead of S | | nothing | nothing | none; nothing | |
| `remove_frame`: as `remove`, raised from the frame (no modal dialog) | | | **ID_YES** | | |

More keys tried:

| Variant | Key | Answer |
| --- | --- | --- |
| `discard` | Alt+Numpad4 | **ID_YES = discard changes** |
| `remove` | Alt+Numpad2 | ID_NO = back to editing |
| `system` | Alt+F10 | **ID_YES = 是(Y)** |

## Explanation

A key pressed with Alt presses the button whose access key has the same character code as the key's virtual-key code. The data fits this rule in every run, and neither the button's position nor the default button changes the result:

- F4 is VK 0x73, which is `s`. Alt+F4 presses "(S)" whether it sits on Yes or No, from a dialog and from a frame, and does nothing when no button has S.
- Numpad4 is VK 0x64, which is `d`: Alt+Numpad4 presses "放棄變更(D)". Numpad2 is VK 0x62, which is `b`: Alt+Numpad2 presses "返回編輯(B)".
- F10 is VK 0x79, which is `y`: Alt+F10 presses "是(Y)" in the system box.

Every letter a-z has such a key: a-i are Numpad1-9, j-o are the numpad operators, and p-z are F1-F11. A native Yes/No box therefore always has some Alt+key that presses its affirmative button. The keys the user named are Esc, Alt+F4 and the close button. Of these, only Alt+F4 matters, and it hits the "(S)" button.

The probe agrees with F-11's planning measurement (OK/Cancel box with custom labels: Alt+F4 answers OK, which was "移除並儲存(&S)"). It also explains that measurement: the cause is the access key S, not the button's position.

## Consequences for F-13

- The removal box with "移除並儲存(&S)" fails the user's precondition (Alt+F4 removes the rows and saves). Item 5 is not done, and both boxes stay `wx.GenericMessageDialog` (spec D5).
- The discard box alone would pass the precondition as stated. But Alt+Numpad4 would discard the changes, and the user asked for both boxes to change together or not at all.
- Pre-existing and not in F-13: in the existing system Yes/No boxes, Alt+F10 answers 是(Y). This was measured on a box raised from a modal dialog, as the dictionary delete confirmation in Dictionary Management is. It was not measured for the three boxes raised from the main window. The spec lists this as a follow-up for the user.
