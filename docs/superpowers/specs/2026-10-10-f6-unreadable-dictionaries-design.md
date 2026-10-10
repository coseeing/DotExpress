# Unreadable Dictionaries (F-6) Design

## Goal

Task F-6 fixes F-W12 (`docs/superpowers/history/2026-10-09-03-windows-verification/auto-results.md`, "新發現"): when any dictionary file in the dictionary folder cannot be read, choosing Dictionary Management does nothing. No window opens and no message appears. The usual cause is a CSV that Excel saved as Big5 (cp950): on Traditional Chinese Windows, "Save As -> CSV (Comma delimited)" writes Big5, so one save from Excel locks the user out of Dictionary Management. A file that is denied by its ACL, held open without read sharing, or not valid CSV has the same effect.

Decided by the user (2026-10-10, HANDOFF section 5.3, item 2; not re-asked here):

- **U1.** The entry-count column shows "無法讀取" ("Unreadable") for a dictionary that cannot be read. The other dictionaries show their counts as before. When the user selects an unreadable dictionary, the dialog explains why, for example "not UTF-8, save it again as CSV UTF-8".
- **U2.** No automatic detection or reading of Big5. Guessing the encoding can be wrong, and pressing OK in the editor would then silently rewrite the user's file as UTF-8.

After this task:

- Dictionary Management always opens. Each dictionary is read on its own; a file that fails is shown as `無法讀取` and the failure is written to `gui.log`. The dialog also stays correct after Add, Delete, Rename and Import inside it.
- When an unreadable dictionary is selected, a labeled, read-only text field appears under the list with the reason and what to do. It comes right after the list in the Tab order. Edit on that dictionary shows the same reason in an error box and keeps the dialog open; it re-reads the file first, so a file the user fixed meanwhile opens normally.
- Import reads the whole file before copying it. A file that is not UTF-8 or not valid CSV is refused with the same reason text, instead of the misleading header message (small Big5 files) or a silent import of a file that cannot be read (Big5 files whose first 8 KiB are ASCII).
- Delete, Rename and Export keep working on an unreadable dictionary, unchanged. Conversion is unchanged.

New user-visible strings: 7 (msgids 357 -> 364), translated in `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, with `.pot` and `.mo` regenerated.

Non-goals: reading or converting Big5 (U2), a per-cause conversion error, an "open dictionary folder" command, live reloading of counts, the `wx.MessageBox` button language (F-W9, task F-7), header-less or empty CSV files (they still count as 0 entries), and every other item of HANDOFF section 6.

## Current State (verified 2026-10-10 on `fix/f6-unreadable-dictionaries`, HEAD `e46ff26`, Windows 11 26200, NTFS)

`$PY` is `D:\workspace\DotExpress\client\.venv\Scripts\python.exe` (Python 3.13, wxPython 4.2.5 msw). `$SP` is the session scratchpad. The prototypes behind this spec are in `$SP\f6\` (`probe.py`, `today.py`, `proto.py`, `drive2.py`, `sizes.py`; not committed). They run against scratch copies in `%TEMP%` only.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 1307 tests`, `FAILED (errors=1, skipped=7)`. The only error is F-W6 (`test_case_only_rename_still_renames`). Source msgids: 357 (`dotexpress.po` has 358 `msgid` lines including the header).

### Where dictionary files are read

| Reader | Used by | Behavior on a bad file |
| --- | --- | --- |
| `load_dictionary_rows` / `load_dictionary_entries` (`client/dictionaries/entries.py:68-109`, tabs): `open(encoding="utf-8-sig", newline="")`, `csv.DictReader`, every row | the count column of Dictionary Management (`dialog.py:578-582`), the entries editor (`DictionaryEntryListModel.load`, `entry_list_model.py:66-68`) | raises |
| `validate_dictionary_csv` (`client/dictionaries/manager.py:41-47`, 4 spaces): same `open`, reads **only the header** | Import (`import_dictionary`, `manager.py:62-72`) | raises only for what the first decoded chunk contains |
| `LoadedDictionaryRules.from_paths` (`client/conversion/text/dictionary_rules.py:136-200`) | conversion, on the worker thread | raises; caught as `ConversionStageError("translation", ...)` |

`DictionaryManagementDialog.__init__` (`dialog.py:503-520`) calls `refresh_dictionaries`, which sets `self._dictionary_names` and then calls `_load_dictionary_counts`, a dict comprehension over every name. One exception ends the constructor. `on_open_dictionary_management` (`gui.py:995-1006`) does not catch it. The packaged build is built with `--noconsole` (`client/DotExpress.spec:36`), installs no `sys.excepthook`, and wxPython prints handler exceptions to `sys.stderr`, which is `None` there. Nothing is shown and nothing is logged.

### Measurements (`probe.py`, `today.py`)

Python 3.13 on Windows:

| File | `load_dictionary_entries` | `validate_dictionary_csv` (Import) | Conversion message today (zh-TW) |
| --- | --- | --- | --- |
| Big5, CJK in row 2 | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte` | same `UnicodeDecodeError` | `轉譯失敗：'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte` |
| Big5, first CJK after 16 KiB of ASCII rows | `UnicodeDecodeError` (position 325 of a later chunk) | **passes**; Import copies the file | same kind |
| UTF-16 with BOM | `UnicodeDecodeError` (byte 0xff, position 0) | same | same kind |
| a field longer than 131,072 characters (in practice an unclosed `"` in a file over 128 KiB) | `_csv.Error: field larger than field limit (131072)` | passes (header only) | `轉譯失敗：field larger than field limit (131072)` |
| NUL in a field; unterminated quote in a small file; stray quotes | loads (Python 3.11+ no longer raises) | passes | rules loaded |
| empty file; header without `text`/`braille`/`type` | 0 entries | `ValueError` (header message) | `轉譯失敗：CSV must contain header row.` / `...columns: text, braille, type` |
| held open by another process, share none | `PermissionError [Errno 13]`, **`winerror` None** | same | - |
| held open, share read or read+write | loads | - | - |
| ACL deny read (`icacls /deny %USERNAME%:(R)`) | `PermissionError [Errno 13]`, `winerror` None | same | `轉譯失敗：[Errno 13] Permission denied: '...'` |

`open()` goes through the C runtime, which maps both `ERROR_SHARING_VIOLATION` (32) and `ERROR_ACCESS_DENIED` (5) to `EACCES` and leaves `winerror` unset. **A file in use and a file without read permission cannot be told apart** when it is opened for reading. (Rename and delete go through Win32 and do report `[WinError 32]` versus `[WinError 5]`.)

Other operations on such files (current code, no change needed):

| Operation | Big5 | held open, share none | ACL deny read |
| --- | --- | --- | --- |
| Rename (`Path.rename`) | works | `[WinError 32]` -> `儲存字典失敗：...` | `[WinError 5]` -> `儲存字典失敗：...` |
| Delete (`unlink`) | works | `[WinError 32]` -> `無法刪除字典：...` | works |
| Export (`shutil.copyfile`) | works, bytes identical | `[Errno 13]` -> `匯出字典失敗：...` | `[Errno 13]` -> `匯出字典失敗：...` |

### Findings requested by the handoff (section 5.1)

- **(a) Conversion with an unreadable dictionary selected** is not silent. The worker catches the error (`conversion/output.py:66-80`) and `ConversionPresenter._on_job_failure` shows an error box: `轉譯失敗：'utf-8' codec can't decode byte 0xbb in position 19: invalid start byte` (Big5) or `轉譯失敗：[Errno 13] Permission denied: '<full path>'` (denied or locked). The text is the raw Python error. The dictionary is read only when the text has a plain-text segment. A math-only text converts without reading it.
- **(b) Import of a Big5 dictionary.** The name dialog appears first. Then:
  - CJK within the first 8 KiB (the usual case): `UnicodeDecodeError` is a `ValueError`, so `DictionaryManagementPresenter.import_from_file` shows `匯入的檔案必須包含 text、braille 與 type 表頭。`, which is wrong. Nothing is copied.
  - Only ASCII in the first 8 KiB: the header check passes and the file is copied. The dialog's refresh then raises inside the button handler (`today.py`): `_dictionary_names` already holds the new name, the virtual list keeps the old item count and the old counts, so the list is wrong: in `today.py` it shows `alpha` / `1` and `big5` / `0`, and `default` is cut off. Nothing is shown. The next Dictionary Management does nothing.
  - A file whose header line exceeds the CSV field limit would raise `csv.Error`, which the presenter does not catch (theoretical).
- **(c) Delete, Rename, Export.** Today none of them is reachable, because the dialog does not open. Inside an open dialog (a file that went bad after opening) they behave as in the table above, and every successful Rename, Delete, Add or Import then breaks the list as in (b). Edit closes the dialog and `DictionaryEntriesDialog` raises in its constructor: nothing opens, nothing is shown. After F-6 Delete, Rename and Export keep their current behavior (D7). The refresh after them no longer fails (D2), and Edit explains the problem (D5).
- **Leak (minor).** A constructor that raises leaves a hidden, never destroyed `wx.Dialog` (`today.py`: `wx.GetTopLevelWindows()` still lists `字典管理`). It is a child of the frame and goes away with it.

### Accessibility measurements (`proto.py`, `drive2.py`, `sizes.py`; wx 4.2.5 msw)

- A `wx.TextCtrl` with `wx.TE_READONLY` and **without** `wx.TE_MULTILINE` is skipped by Tab. wxMSW's `wxTextCtrl::AcceptsFocusFromKeyboard` refuses keyboard focus for a read-only single-line control. With `wx.TE_MULTILINE | wx.TE_READONLY` it is the next Tab stop after the list.
- A `wx.StaticText` created immediately before the text control becomes its accessible name. UIA reports the Edit as `name='無法讀取的原因：'` with the reason as its value.
- A hidden control is absent from the UIA tree and from the Tab order.
- The prototype's 57-character reason wraps to 2 lines at the dialog's width (`EM_GETLINECOUNT` = 2). After `ChangeValue` and `SelectAll()`, the selection `EM_GETSEL` = `(0, 57)` survives `SetFocus` through UIA. NVDA behavior (known from NVDA, not measured here; item 52 checks it): when an edit gets focus with a collapsed selection, NVDA reads the line at the caret, which is only the first wrapped line; when text is selected, it reads the selection.
- Dialog height (`sizes.py`, wx logical pixels; the display runs at 125 %): if the row is hidden before `SetSizerAndFit`, the dialog has today's size and the list loses the row's height while the row is shown (154 -> 88 px with the default two-line field). If the row is shown during the fit, the dialog grows by that amount instead.

## Decisions

**D1. One helper module classifies and describes read errors: `client/dictionaries/read_problems.py` (new, tabs, no wx).**

```python
class DictionaryReadProblem(Enum):
	NOT_UTF8 = "not_utf8"        # UnicodeDecodeError
	CANNOT_OPEN = "cannot_open"  # PermissionError: in use, or no permission (not distinguishable)
	INVALID_CSV = "invalid_csv"  # csv.Error
	OTHER = "other"              # anything else, including other OSErrors

def classify_dictionary_read_error(error: Exception) -> DictionaryReadProblem
def describe_dictionary_read_error(error: Exception) -> str            # the reason, translated at call time
def describe_unreadable_dictionary(name: str, error: Exception) -> str # headline + "\n\n" + reason
def log_dictionary_read_error(path: Path, error: Exception) -> None    # D8

@dataclass(frozen=True)
class DictionaryCount:
	entries: int = 0
	error: Exception | None = None   # None: readable

def read_dictionary_count(path: Path) -> DictionaryCount
```

- Classification order: `UnicodeDecodeError` before anything else (it is a `ValueError`), then `PermissionError`, then `csv.Error`, else `OTHER`.
- `read_dictionary_count` returns `DictionaryCount(len(load_dictionary_entries(path)))`. On any `Exception` it calls `log_dictionary_read_error(path, error)` and returns `DictionaryCount(error=error)`. It counts exactly what the editor shows, unchanged since F-4.
- One combined `CANNOT_OPEN` reason, because the two causes cannot be told apart (Current State). A per-cause check through `CreateFileW` would add Windows-specific code for a message that already names both causes.
- The reasons never mention Big5. A file in any other encoding gets the same advice (U2).

**D2. The count column (U1).** `DictionaryManagementDialog` keeps `_dictionary_counts: dict[str, int]` for readable dictionaries and gains `_dictionary_read_errors: dict[str, Exception]`. `_load_dictionary_counts` fills both through `read_dictionary_count`, and it never raises for a file. `_get_item_text(item, 1)` returns `_("Unreadable")` for a name in `_dictionary_read_errors`, else the count as today. Counts are read when the dialog opens, after each successful Add, Delete, Rename or Import inside it (`refresh_dictionaries`, unchanged call sites), and for the selected dictionary on Edit (D5). They are not polled. `_resize_columns` sizes the count column for the wider of `_("Entries")` and `_("Unreadable")`. Both are four characters in zh-TW, so nothing changes in the shipped language.

**D3. The reason row (U1, "explain after selection").** `_build_ui` creates, right after the list and before the action buttons (creation order is Tab order and accessible-name order):

```python
self.read_problem_label = wx.StaticText(self, label=_("Why this dictionary cannot be read:"))
self.read_problem_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, <about three text lines>))
```

Both are added to the main sizer under the list (label with `LEFT | RIGHT`, field with `EXPAND | LEFT | RIGHT | BOTTOM`, border 12) and hidden before `finalize_dialog_layout`, so the dialog keeps today's size. `_update_read_problem()` runs at the end of `refresh_dictionaries` and in `_on_selection_changed`:

- If the selected dictionary (`_get_selected_name()`) has a read error: `read_problem_ctrl.ChangeValue(describe_dictionary_read_error(error))`, then `SelectAll()`, show the label and the field, then `Layout()`.
- Otherwise: `ChangeValue("")`, hide both, then `Layout()`.

Rationale and accessibility:

- **NVDA path.** Selecting the row makes NVDA read the list item with its count column, which says `無法讀取`. One Tab reaches the field. NVDA reads its label `無法讀取的原因：`, its role (edit, multi-line, read-only) and, because the text is selected, the whole reason, not just the first wrapped line. Shift+Tab returns to the list. The field is read-only and takes no input. `ChangeValue` sends no text event.
- **Nothing changes when every dictionary is readable.** The row is hidden, so it is not in the Tab order, not in the UIA tree and takes no space. The dialog is the same size as today.
- **No automatic announcement on selection.** wxPython offers no live-region or UIA notification call. The column already says `無法讀取` when the row is selected, and Edit explains it in a message box (D5). A ctypes UIA notification would be new platform code for a hint that is one key away.
- Rejected:
  - A read-only single-line field: Tab skips it (measured).
  - A `StaticText`: not focusable, so NVDA users would have to use object navigation.
  - A status bar: the dialog has none.
  - A row that is always visible: an extra, empty Tab stop for every user.
  - A message box on selection: it interrupts arrowing through the list.

**D4. Strings and wording.** See "User-Visible Strings". The reasons are full sentences, so they read the same in the field, in the Edit box and after `匯入字典失敗：` on Import. `INVALID_CSV` and `OTHER` append Python's error text, as the existing `Failed to ...: {error}` messages do (F-3 D6).

**D5. Edit on an unreadable dictionary stays in the dialog.** `_on_edit`:

1. No selection: return (unchanged).
2. Read the selected dictionary again with `read_dictionary_count` and store the result in the two dicts. Refresh the list and `_update_read_problem()`.
3. If it has an error: `self.show_error(describe_unreadable_dictionary(name, error))` (the existing view method: `wx.MessageBox(..., _("Error"), wx.OK | wx.ICON_ERROR)`) and return. The dialog stays open with the selection unchanged, and `edit_dictionary_name` stays `None`.
4. Otherwise: as today, `edit_dictionary_name = name; EndModal(wx.ID_EDIT)`.

The re-read means a file that the user saves again as CSV UTF-8 (or closes in the other program) while the dialog is open opens at the next Edit, and its count is updated. The Edit button stays enabled for unreadable dictionaries (`get_action_availability` is unchanged). Disabling it would hide the explanation from keyboard users.

**D6. The editor may still fail to read the file (race), so `on_open_dictionary_management` guards the editor.** If the file goes bad between the check in D5 and the `DictionaryEntriesDialog` constructor, the constructor raises. The handler catches `Exception`, calls `log_dictionary_read_error(dictionary_path, error)` and shows `wx.MessageBox(describe_unreadable_dictionary(edit_name, error), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)`. The management dialog has closed by then, as today, and the user can open it again. The editor's construction order is not changed: the hidden half-built dialog stays a child of the frame (Current State, "Leak"). This guard adds one `wx.MessageBox` call to `gui.py`, which F-7 must include in its count.

**D7. Delete, Rename and Export are unchanged for an unreadable dictionary.** They stay enabled and use the presenter's existing code and messages (table in Current State). They are how the user gets out: Export copies the bytes unchanged, so the file can be fixed in Excel elsewhere and imported again; Delete removes a broken copy. After each one, `refresh_dictionaries` no longer fails (D2), so the list and the reason row are correct. The default dictionary still cannot be deleted or renamed. If `default.csv` itself is unreadable, the user fixes it in place, and the reason text says how.

**D8. Logging.** Every failed read in D1, D5 and D6 is logged at `ERROR` to the existing `dotexpress.gui` logger (`get_logger("dotexpress.gui", "gui.log")`, the file that F-3 and F-5 already use for UI errors):

- `UnicodeDecodeError`, `csv.Error` or any `OSError`: one line, no traceback: `Cannot read dictionary "%s": %s: %s` with `path.name`, the exception type name and the error text. These failures are expected, come from the user's data, and are fully described by the message.
- Anything else: `Unexpected error while reading dictionary "%s"` with `exc_info=error` (traceback), as F-3 M-3 does for non-`OSError` save errors.

In the packaged build the log is `<folder of DotExpress.exe>\log\gui.log` (`app_paths.get_application_root` returns the executable's folder when frozen; `log.get_logger` creates the file at the first record). No UI points to it, and no new string is needed. Log texts are not translated. A dictionary that stays unreadable is logged again at every refresh and every Edit. That is a few lines per dialog use (Risks).

**D9. Import reads the whole file before copying it.** `validate_dictionary_csv` (`manager.py`, 4 spaces) reads the header, checks it as today (missing columns still raise the same `ValueError`), then iterates over every row inside the same `with` block. It reads the file exactly as `load_dictionary_rows` does (same `open` arguments, same `DictReader`), so any file Import accepts can also be counted and edited. `DictionaryManagementPresenter.import_from_file` gains, **before** `except ValueError` (because `UnicodeDecodeError` is a `ValueError`):

```python
except (UnicodeDecodeError, csv.Error) as exc:
	view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))
	return None
```

Header errors, invalid names and `OSError` (including a source file that is in use or denied) keep their current messages. Nothing is copied when validation fails, as today. Import does not log: the user sees the reason, and nothing was changed.

**D10. Conversion is unchanged.** With an unreadable dictionary selected, conversion shows `轉譯失敗：<Python error>` as today (finding a). A friendlier conversion message is a follow-up (Open Questions O5).

**D11. Catalogs.** Seven new msgids: `dialog.py` (2), `dictionaries/read_problems.py` (5). Regenerate with `scripts\generate-pot.bat`, pin `POT-Creation-Date` to `2026-10-10 12:00+0800`, run `msgmerge --update --backup=none locales\zh_TW\LC_MESSAGES\dotexpress.po locales\dotexpress.pot`, fill the msgstr values, and remove any `fuzzy` flag that `msgmerge` adds. `msgmerge` may fuzzy-match `Dictionary "{name}" cannot be read.` to `Dictionary "{name}" already exists.` and `The file cannot be read: {error}` to another `...: {error}` entry; check each new entry. Build with `msgfmt --check -o locales\zh_TW\LC_MESSAGES\dotexpress.mo locales\zh_TW\LC_MESSAGES\dotexpress.po`. `msgfmt --check --statistics` must report 364 translated messages, 0 fuzzy and 0 untranslated. `msgfmt` 0.23 is installed. If it is missing, build the `.mo` with a script that is first shown to give byte-identical output for the current `.po` (AGENTS.md).

## Behavior per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Open Dictionary Management, all files readable | dialog with counts | identical; reason row hidden |
| Open Dictionary Management, one file unreadable (any cause) | nothing happens (F-W12) | dialog opens; that row shows `無法讀取`; others show counts; one `gui.log` line per unreadable file |
| Select an unreadable dictionary | - | reason row appears under the list with the reason, text selected; Tab reaches it |
| Select a readable dictionary | - | reason row hidden |
| Edit, unreadable dictionary | - (dialog cannot open; if the file went bad while open: dialog closes, nothing opens, nothing shown) | error box `無法讀取字典「name」。` + reason; dialog stays open; logged |
| Edit, file fixed while the dialog is open | - | count updated; editor opens |
| Edit, file goes bad between the check and the editor | nothing shown | error box from the frame (D6); logged |
| Delete / Rename / Export, unreadable dictionary | not reachable (or list broken afterwards) | existing behavior and messages; list correct afterwards |
| Add / Import / Rename / Delete while another file is unreadable | list broken, nothing shown | list correct; the other file still `無法讀取` |
| Import Big5 (CJK in the first 8 KiB) | `匯入的檔案必須包含 text、braille 與 type 表頭。` | `匯入字典失敗：檔案不是以 UTF-8 儲存。...`; nothing copied |
| Import Big5 (ASCII-only first 8 KiB) | copied; list broken; dialog dead afterwards | refused with the same message; nothing copied |
| Import a file with a field over the CSV limit | copied (header passes) | `匯入字典失敗：檔案不是有效的 CSV 檔案。...`; nothing copied |
| Import without the required headers; invalid name; source in use or missing | existing messages | identical |
| Convert with an unreadable dictionary selected | `轉譯失敗：<Python error>` | identical |
| Empty or header-less dictionary | count 0; conversion fails with the header message | identical |

## Design per File

### `client/dictionaries/read_problems.py` (new, tabs)

D1, D8. Module docstring: "Why a dictionary file cannot be read, in words the user can act on (F-6). Nothing here imports wx." `logger = get_logger("dotexpress.gui", "gui.log")` at module level.

### `client/dialog.py` (tabs)

- Import `read_dictionary_count`, `describe_dictionary_read_error`, `describe_unreadable_dictionary`; `load_dictionary_entries` is no longer imported here if nothing else uses it.
- `DictionaryManagementDialog.__init__`: `self._dictionary_read_errors: dict[str, Exception] = {}`.
- `_build_ui`: the reason row (D3), hidden before `finalize_dialog_layout`.
- `_get_item_text`, `_load_dictionary_counts` (D2), `_store_count(name, count)`, `_update_read_problem()` (D3), `refresh_dictionaries` and `_on_selection_changed` call it, `_resize_columns` (D2), `_on_edit` (D5).
- Not changed: `DictionaryEntriesDialog`, `localize_standard_buttons`, the view methods (`show_error` is reused).

### `client/gui.py` (tabs)

`on_open_dictionary_management`: the editor guard of D6. Import `describe_unreadable_dictionary`, `log_dictionary_read_error`.

### `client/dictionaries/manager.py` (4 spaces)

`validate_dictionary_csv` reads every row (D9). Docstring: "Raise ValueError if a header is missing; reading every row raises what reading the dictionary later would (UnicodeDecodeError, csv.Error, OSError)."

### `client/dictionaries/presenter.py` (tabs)

`import_from_file`: the `except (UnicodeDecodeError, csv.Error)` branch of D9, before `except ValueError`.

### `client/locales/`

`dotexpress.pot`, `zh_TW/LC_MESSAGES/dotexpress.po`, `zh_TW/LC_MESSAGES/dotexpress.mo` (D11).

### Tests and stubs

`client/tests/wx_stub.py` only if `speech_dialog_stubs` lacks what the new dialog code needs (`TE_MULTILINE`, `TE_READONLY`, `StaticText`, `TextCtrl` are created automatically by `AutoSubmoduleModule`; the plan checks). New `client/tests/test_dictionary_read_problems.py` (tabs, like the other dictionary tests).

### Not changed

`dictionaries/entries.py`, `dictionaries/entry_list_model.py`, `dictionaries/actions.py`, `dictionaries/name_prompt.py`, `conversion/` (D10), `ui/conversion_presenter.py`, `settings/`, the dictionary file format, `client/dictionary/`, `client/braille/`.

## What Stays Identical

- The bytes of every dictionary file: F-6 only reads. Nothing converts, repairs or rewrites a file (U2).
- The count of a readable dictionary (rows the editor shows, F-4).
- Button availability, the order of the buttons, the dialog size and the Tab order when every dictionary is readable.
- Every existing message and caption, and the Import messages for missing headers, invalid names and `OSError`.
- Conversion, the entries editor, and Delete, Rename and Export.
- Both fixture sha256 values (`translation_golden.json` `e67d95a1...`, `dictionary_entries_trace.json` `f493da52...`).

## User-Visible Strings

New msgids (357 -> 364):

| msgid | msgstr (zh_TW) | Where |
| --- | --- | --- |
| `Unreadable` | `無法讀取` | count column (`dialog.py`) |
| `Why this dictionary cannot be read:` | `無法讀取的原因：` | label of the reason field (`dialog.py`) |
| `Dictionary "{name}" cannot be read.` | `無法讀取字典「{name}」。` | headline of the Edit error box (`read_problems.py`) |
| `The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, for example with Save As in Excel.` | `檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。` | reason `NOT_UTF8` |
| `The file cannot be opened. It may be in use by another program, or you may not have permission to read it. Close the other program and try again.` | `無法開啟檔案。檔案可能正被其他程式使用，或您沒有讀取權限。請關閉其他程式後再試一次。` | reason `CANNOT_OPEN` |
| `The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}` | `檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}` | reason `INVALID_CSV` |
| `The file cannot be read: {error}` | `無法讀取檔案：{error}` | reason `OTHER` |

Reused: `Error` (`錯誤`) as the caption of both error boxes, and `Failed to import dictionary: {error}` (`匯入字典失敗：{error}`) on Import. `CSV UTF-8` and `Excel` stay as they are in zh-TW (product and format names as Excel shows them). The format name in the `NOT_UTF8` reason is the one Excel lists in its Save As dialog: `CSV UTF-8 (Comma delimited)` in English Excel and `CSV UTF-8 (逗號分隔)` in Traditional Chinese Excel. The messages with `{error}` get `#, python-brace-format` from `xgettext`.

The Edit box reads, in zh-TW:

```
無法讀取字典「big5」。

檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，例如在 Excel 中使用「另存新檔」。
```

## Test Plan

TDD: each step's new tests are written first and fail for the stated reason; then the code turns them green. Test files keep their indentation: `test_dictionary_management_dialog.py`, `test_dictionary_presenter.py` and the new file use tabs; `test_dictionary_manager.py`, `test_gui_document_flows.py` and `test_i18n.py` use 4 spaces.

**Log isolation is mandatory.** `read_problems` binds a `FileHandler` for `client/log/gui.log` when it is imported. Every test module that can make it log must call `unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))` in `setUpModule`, as `test_gui_document_flows.py` does. This applies to the new read-problems tests and to `test_dictionary_management_dialog.py`. `test_gui_document_flows.py` already does it. Log assertions use `self.assertLogs("dotexpress.gui", level="ERROR")` and check `record.exc_info`.

Test data is built in temporary directories: Big5 via `"...".encode("cp950")`, a late-Big5 file (about 16 KiB of ASCII rows, then one CJK row), a field-limit file (`"x" * 140000`), and UTF-16. `PermissionError` is injected with `patch.object(read_problems, "load_dictionary_entries", side_effect=PermissionError(13, "Permission denied"))`. The Windows-only tests use `windows_file_handles.hold_open(self, path, 0)` (share none). Tests never touch `client/dictionary/`, `client/workspace/`, `client/config.json` or `client/log/`.

### R. Read problems (`client/tests/test_dictionary_read_problems.py`, new)

1. `test_classifies_each_error` (subTests): a real Big5 `UnicodeDecodeError` -> `NOT_UTF8`; `PermissionError` -> `CANNOT_OPEN`; `csv.Error` -> `INVALID_CSV`; `FileNotFoundError`, `OSError(22, ...)`, `RuntimeError` -> `OTHER`.
2. `test_describes_each_problem`: the text equals `read_problems._(<msgid>)`, formatted with `error` where the msgid has `{error}`. Comparing through the module's `_` keeps the test valid before and after the catalog step.
3. `test_unreadable_dictionary_message_has_headline_and_reason`.
4. `test_count_of_readable_and_missing_files` (subTests: UTF-8, UTF-8 with BOM, F-4's `DICT_BADBOPO` counts 1, missing file counts 0): no error, `assertNoLogs`.
5. `test_count_of_unreadable_file_returns_the_error_and_logs_one_line` (subTests: Big5, late Big5, UTF-16, field limit, injected `PermissionError`): `entries == 0`, the error type, one `ERROR` record naming the file, `exc_info` is `None`.
6. `test_unexpected_error_is_logged_with_traceback`: `RuntimeError("injected")` -> record with `exc_info`.
7. Windows only: `test_file_held_open_without_sharing_cannot_be_opened`: `hold_open(..., 0)` -> `CANNOT_OPEN`.
8. `test_module_does_not_import_wx`.

### M. Management dialog (`client/tests/test_dictionary_management_dialog.py`)

`_make_dialog` gains `_dictionary_read_errors = {}`, fake `read_problem_label` and `read_problem_ctrl` objects (they record `Show`, `ChangeValue` and `SelectAll`), `Layout = Mock()` and `show_error = Mock()`.

1. `test_unreadable_dictionary_shows_unreadable_and_the_others_their_counts`. Red: `UnicodeDecodeError`.
2. `test_refresh_after_an_action_keeps_names_counts_and_item_count_consistent`: a late-Big5 file appears after `_on_import_clicked`. Red.
3. `test_each_unreadable_dictionary_is_logged`.
4. `test_selecting_an_unreadable_dictionary_shows_the_reason`: `ChangeValue(reason)`, `SelectAll`, both shown, `Layout`.
5. `test_selecting_a_readable_dictionary_hides_the_reason`: empty value, both hidden.
6. `test_refresh_shows_the_reason_for_the_preferred_selection`.
7. `test_edit_on_an_unreadable_dictionary_shows_the_error_and_stays_open`: `show_error(describe_unreadable_dictionary(...))`, no `EndModal`, `edit_dictionary_name` stays `None`.
8. `test_edit_after_the_file_was_fixed_opens_the_editor_and_updates_the_count`.
9. `test_edit_on_a_dictionary_that_became_unreadable_stays_open`: readable at refresh, Big5 written before Edit.
10. `test_unreadable_dictionaries_keep_delete_rename_and_export_enabled` (non-default name; default keeps Delete and Rename disabled).
11. `test_count_column_fits_the_unreadable_label`.
12. Windows only: `test_dictionary_held_open_without_sharing_is_unreadable_with_the_cannot_open_reason`.

Still green unchanged: every existing test in the file, including `test_only_explicit_edit_handler_sets_edit_result` (missing file: readable, 0 entries).

### P. Import (`test_dictionary_manager.py`, `test_dictionary_presenter.py`)

1. Manager: `test_validate_reads_every_row` (subTests: late Big5 -> `UnicodeDecodeError`; field limit -> `csv.Error`). Red: they pass today. `test_import_dictionary_refuses_a_late_big5_file_and_copies_nothing`. Red: it is copied today.
2. Presenter: `test_import_big5_shows_the_not_utf8_reason` (expected `("error", _("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(<the error>)))`; nothing copied). Red: the header message today. `test_import_late_big5_is_refused`. Red: imported today. `test_import_invalid_csv_shows_the_reason`. Red: imported today.
3. Unchanged and green: `test_import_without_headers_shows_header_error`, `test_import_invalid_name_shows_header_error`, `test_import_missing_source_shows_import_error`, and the rest.

### G. Frame (`client/tests/test_gui_document_flows.py`, class `DictionaryManagementFrameTest`)

1. `test_editor_that_cannot_read_its_dictionary_shows_the_reason`: `editor_class.side_effect = <Big5 UnicodeDecodeError>`; the handler returns normally; one `MessageBox(describe_unreadable_dictionary("alpha", error), _("Error"), OK | ICON_ERROR, parent=frame)`; one log line without `exc_info`. Red: the exception propagates.
2. `test_editor_failure_that_is_unexpected_is_logged_with_its_traceback`: `RuntimeError`.

### I. Catalog (`client/tests/test_i18n.py`)

1. `test_unreadable_dictionary_strings_are_translated`: `i18n.load_translation()` maps the seven msgids to the zh-TW texts above.

### Counts

New tests: R 8, M 12, P 5 (manager 2, presenter 3), G 2, I 1 = 28 (3 Windows-only tests are skipped on POSIX). Expected on Windows: `Ran 1335`, `FAILED (errors=1, skipped=7)`, F-W6 only. The plan may adjust the counts and split subTests differently; the red/green intent is binding.

## Migration Steps (each step one green commit, red first)

1. `fix: open Dictionary Management when a dictionary cannot be read (F-6)`: D1, D2, D8. R 1-8 and M 1-3, 10, 11, 12. The reason texts exist as English msgids from this step on.
2. `fix: explain why a dictionary cannot be read (F-6)`: D3, D5, D6. M 4-9, G 1-2.
3. `fix: refuse importing a dictionary that cannot be read (F-6)`: D9. P 1-2.
4. `chore: translate the unreadable-dictionary strings (F-6)`: D11, I 1; `.pot`, `.po` and `.mo`.

Each commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and stages explicit paths only.

## Acceptance Criteria

Run on Windows from `client/` with `$PY`.

1. Full suite: no failure or error other than F-W6; `Ran` = 1307 + the new tests.
2. Focused: `$PY -m unittest tests.test_dictionary_read_problems tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_presenter tests.test_gui_document_flows tests.test_i18n tests.test_dictionary_entries -v` passes; the Windows-only tests run (not skipped).
3. Catalogs: 364 source msgids by an `$PY -I` AST scan of `_`/`N_`; `msgfmt --check --statistics` reports 364 translated, 0 fuzzy, 0 untranslated; the `.mo` translates the seven msgids; `scripts\generate-pot.bat` run twice gives identical output apart from `POT-Creation-Date`.
4. Both fixture sha256 values unchanged.
5. App data untouched: the sha256 of every file under `client/dictionary/`, `client/workspace/`, `client/log/` and `client/config.json` is identical before and after the suite (the spec session recorded the starting list in `$SP\f6\userdata-before.txt`). In particular, no test writes to `client/log/gui.log`.
6. `git diff main --stat` touches only `client/dictionaries/read_problems.py`, `client/dialog.py`, `client/gui.py`, `client/dictionaries/manager.py`, `client/dictionaries/presenter.py`, the three locale files, the test files named above (and `wx_stub.py` if needed), and the spec, plan and history files.
7. Mutation check (plan): each mutant is caught by at least one test:
   - `_load_dictionary_counts` without the per-file catch;
   - an unreadable file counted as `0`;
   - the classification order with `ValueError`/`OTHER` before `UnicodeDecodeError`;
   - no log line, or a traceback for a `UnicodeDecodeError`;
   - no traceback for an unexpected error;
   - the reason row not hidden for a readable selection, or no `SelectAll`;
   - Edit without the re-read;
   - Edit that closes the dialog on an unreadable dictionary;
   - the frame without the editor guard;
   - `validate_dictionary_csv` reading only the header;
   - the presenter's new branch after `except ValueError`.
8. Packaged GUI verification below, with results in the implementation's history folder.

## Windows Verification (packaged build)

Build as in F-5: the main checkout's `client\.venv\Scripts` first on `PATH`, `scripts\build-dotexpress.bat`. Check in `client\build\DotExpress\PYZ-00.toc` that `dialog.py`, `gui.py` and `dictionaries\read_problems.py` come from the checkout being verified. Copy `client\dist\DotExpress.exe` to `D:\dxtest\N-f6\`. Each item runs in a new `D:\dxtest\auto<N>-f6` folder; only processes whose exe lies under that folder are ended (`dx.kill_under`). The scripts reuse `docs/superpowers/history/2026-10-09-03-windows-verification/auto/` (`dx.py`, `docs.py`, `dicts.py`) and `.../2026-10-10-01-f5-save-failure-handling/auto/f5gui.py` without editing them. New scripts, a helper `f6gui.py` and a share-none locker `lockx.py` (`CreateFileW(GENERIC_READ, share 0)`; `lock.py` only knows `r` and `rw`) go to `docs/superpowers/history/2026-10-10-03-f6-unreadable-dictionaries/auto/`. They run in the pywinauto venv (`$SP\uia`). Test files are generated by script into the item folder: `big5.csv` (`text,braille,type` + `臺北,⠞⠺,Braille` in cp950), `big5_late.csv` (16 KiB of ASCII rows, then a cp950 row) and `badquote.csv` (UTF-8, an unclosed `"` on row 2 followed by more than 128 KiB of rows). Each file's sha256 is recorded before and after each item.

`f6gui.py` reads the list rows through `dicts.mgr_items` and the reason row as the dialog's `Edit` child and the `Static` before it. Through UIA it also records whether the Edit exists, its name and value, and `EM_GETSEL`. Error boxes are read and closed with `f5gui.dismiss` (UIA task dialogs). Keystrokes go to the DotExpress window only after `set_focus()` succeeds. If the foreground is taken by another program, the run is repeated (HANDOFF section 2).

| # | Steps | Expected after F-6 | Before (N-f5b) |
| --- | --- | --- | --- |
| 42 | Start once, close; put `big5.csv` in `dictionary\`; start; open Dictionary Management | the dialog opens; rows `big5` / `無法讀取`, `default` / `0`; no reason row (no `Edit` in the dialog); `log\gui.log` has one line `[ERROR] Cannot read dictionary "big5.csv": UnicodeDecodeError: 'utf-8' codec can't decode byte ...` and no `Traceback`; `big5.csv` bytes unchanged | nothing opens (F-W12) |
| 43 | As 42; select `big5`; then select `default` | `big5`: label `無法讀取的原因：`, Edit with that name and the `NOT_UTF8` zh-TW text, `EM_GETSEL` = whole text; `default`: the row is gone | - |
| 44 | As 43 with `big5` selected; press 編輯 | error box `錯誤`: `無法讀取字典「big5」。` + blank line + the `NOT_UTF8` text; after OK, `字典管理` is still open, no `自訂字典管理器`; a second log line. Then rewrite `big5.csv` as UTF-8 by script and press 編輯 again: the editor opens with row `臺北`; after Cancel, reopening shows count `1` | - |
| 45 | Tab order: with `big5` selected and focus on the list, Tab, then Shift+Tab; with `default` selected, Tab | `big5`: focus goes to the reason Edit, then back to the list; `default`: focus goes to `新增` | - |
| 46 | `icacls dictionary\big5.csv /deny %USERNAME%:(W)` (F-W12's original reproduction, includes SYNCHRONIZE); open; select; 編輯; 匯出 to `D:\dxtest\auto46-f6\out.csv`; restore the ACL | row `無法讀取`; reason `CANNOT_OPEN` text; 編輯: the box with that text; 匯出: today's `匯出字典失敗：[Errno 13] Permission denied: ...`; the dialog stays usable | nothing opens |
| 47 | `lockx.py` holds `dictionary\alpha.csv` (a readable dictionary created through 新增) with share none; open; select `alpha`; release the lock; press 編輯 | `alpha` / `無法讀取`, reason `CANNOT_OPEN`; after the release, 編輯 opens the editor (re-read) | nothing opens |
| 48 | Import `big5.csv` from outside the dictionary folder, name `b1`; import `big5_late.csv`, name `b2` | both: name dialog, then `匯入字典失敗：檔案不是以 UTF-8 儲存。...`; no `b1.csv` or `b2.csv` in `dictionary\`; the list unchanged | `b1`: `匯入的檔案必須包含 text、braille 與 type 表頭。`; `b2`: copied, list wrong, the next open does nothing |
| 49 | Put `badquote.csv` in `dictionary\`; open; select it; then import the same file as `bq2` | row `無法讀取`; reason `檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：field larger than field limit (131072)`; Import: `匯入字典失敗：` + the same reason; nothing copied | nothing opens / Import copies the file |
| 50 | With `big5.csv` present: rename `big5` to `big5x`; export `big5x` to a file; delete `big5x` | rename: the list shows `big5x` / `無法讀取`, selected, reason row shown; export: the output bytes equal the source; delete: confirmation, then the row is gone; no error box | not reachable |
| 51 | With `big5.csv` present: choose `big5` as the dictionary in Settings (`dicts.set_dictionary`); type `臺北` in the input; convert | `轉譯失敗：'utf-8' codec can't decode byte 0xbb ...` (unchanged, D10) | same |
| 52 (manual, user) | With NVDA: open Dictionary Management with `big5.csv` present; arrow to `big5`; Tab; Shift+Tab; press 編輯 | Record what NVDA says. Expected: the row read with `無法讀取`; on Tab, the label `無法讀取的原因`, the role and the **whole** reason; Shift+Tab back to the list; the error box read as a dialog. If NVDA reads only the first line, report it (D3's selection may need a change) | - |

## Interaction with F-7

F-7 (F-W9, M-7, M-5) changes `localize_standard_buttons` and the `wx.MessageBox` sites. F-6 adds no message box to `dialog.py`: Edit reuses `show_error`. F-6 adds one `wx.MessageBox` call to `gui.py` (D6), which F-7's helper must also cover; its count of production `wx.MessageBox` calls becomes 20. The Close button of Dictionary Management still goes through `localize_standard_buttons`, unchanged.

## Risks

- **NVDA might read only part of the reason** (low). The whole text is selected (measured through `EM_GETSEL`), and NVDA reads a selection on focus. The NVDA speech itself is checked only by item 52. Even if it fails, the Edit box reads the full text.
- **Log volume** (low). One line per unreadable file on every dialog open, every refresh and every Edit. Users open the dialog occasionally. The lines are short and carry no traceback.
- **Import refuses files it used to accept** (low, intended). Only files that could not be counted or edited after import are refused (same reader). Their earlier "success" left a broken dictionary and a dead dialog.
- **Import reads the file twice** (validation, then the copy). Dictionaries are small text files; a file changed between the two reads is the same race as today.
- **The list is smaller while the reason row is shown** (low). It loses the row's height (66 logical px with a two-line field in the prototype, more with three lines). The dialog can be resized, and it is unchanged when every dictionary is readable.
- **`CANNOT_OPEN` names two possible causes** (low). It is not possible to tell them apart without extra Win32 calls (measured). The text tells the user to try both remedies.
- **A file can go bad after the counts were read** (low). It is caught by the re-read on Edit (D5) or the guard in the frame (D6). Delete, Rename and Export report their own errors.

## Open Questions

None blocking. The user decided U1 and U2. The decisions below fill in details within them; each is the conservative default.

- **O1. Presentation of the reason.** A labeled multi-line read-only field under the list that appears only for an unreadable selection, with its text selected, plus the explanation in a message box on Edit. No automatic announcement (D3, D5). **Decided by orchestrator with the recommended default; user may override before merge.**
- **O2. One message for "in use" and "permission denied"** (D1). **Decided by orchestrator with the recommended default; user may override before merge.**
- **O3. Import reads the whole file and refuses non-UTF-8 and invalid CSV files with the reason** (D9). This changes one message (Big5 with CJK in the first 8 KiB: the header message becomes the reason) and refuses Big5 files that start with 8 KiB of ASCII, which used to be imported broken. Alternative: leave Import unchanged and drop migration step 3; such an import then shows as `無法讀取` with its reason. **Decided by orchestrator with the recommended default; user may override before merge.**
- **O4. Delete, Rename, Export and Edit stay enabled for an unreadable dictionary** (D5, D7). **Decided by orchestrator with the recommended default; user may override before merge.**
- **O5. Conversion is unchanged** (D10). It still shows the raw Python error. Follow-up: map a `UnicodeDecodeError` or `PermissionError` that comes from the selected dictionary to `Dictionary "{name}" cannot be read.` and the reason. **Decided by orchestrator with the recommended default; user may override before merge.**
- **O6. Logging**: one `ERROR` line for expected errors (decode, CSV, `OSError`), a traceback for anything else, in `gui.log` (D8). **Decided by orchestrator with the recommended default; user may override before merge.**
- **O7. The dialog keeps today's size; the reason row takes space from the list while shown** (D3). **Decided by orchestrator with the recommended default; user may override before merge.**
- **O8. Empty and header-less CSV files still count as 0 entries** (readable), unchanged. **Decided by orchestrator with the recommended default; user may override before merge.**

## Out of Scope / Follow-ups

- O5: a friendly conversion error for an unreadable dictionary.
- An "Open dictionary folder" command, so a broken `default.csv` can be found and fixed from the app.
- Header-less, empty or unclosed-quote files that load with fewer or merged rows (O8). A small file with an unclosed quote loads as one long entry.
- `on_open_dictionary_management` still lets an `OSError` from `ensure_default_dictionary` (an unwritable dictionary folder) escape silently.
- The hidden half-built `DictionaryEntriesDialog` left by a failing constructor (Current State, "Leak").
- F-W9 for the new `wx.MessageBox` call: F-7.
