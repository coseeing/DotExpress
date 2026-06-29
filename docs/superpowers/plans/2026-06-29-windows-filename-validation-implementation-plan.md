# Windows Filename Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓文件與字典共用 Windows 合法檔名規則，允許名稱包含 `.`，並讓字典匯入在複製檔案前顯示已預填來源檔名的可編輯名稱對話框。

**Architecture:** 將 Windows 檔名限制完整集中在 `normalize_base_name()`，文件與字典的 domain wrapper 繼續共用此入口。UI 對話框直接呼叫 domain normalizer 取得一致的驗證結果；字典匯入則把 `Path.stem` 傳給 `DictionaryNameDialog(initial_name=...)`，只有在對話框回傳 OK 後才呼叫 manager 複製 CSV。

**Tech Stack:** Python 3、wxPython、`pathlib`、`unittest`、`unittest.mock`、gettext

---

## File Map

- Modify: `client/name_validation.py` — 實作共用 Windows 檔名字元、結尾、控制字元及保留裝置名稱驗證。
- Modify: `client/tests/test_document_workspace.py` — 覆蓋文件名稱的 Windows 邊界案例、含點號文字匯入與 DEP round trip。
- Modify: `client/tests/test_dictionary_manager.py` — 覆蓋字典名稱的相同 Windows 邊界案例與含點號的匯入目的檔名。
- Modify: `client/dialog.py` — 讓字典名稱對話框接受初始值，並讓兩個名稱對話框委派共用 normalizer 驗證。
- Modify: `client/tests/test_dialog_validation.py` — 驗證 UI 層接受點號、拒絕 Windows 非法名稱，且字典初始值能被設定及選取。
- Create: `client/dictionaries/import_flow.py` — 協調來源檔名預填、使用者確認及 manager 匯入，讓取消語意可在無 wx 環境測試。
- Create: `client/tests/test_dictionary_import_flow.py` — 驗證來源 stem 預填、名稱修改及取消時不匯入。
- Modify: `client/gui.py` — 字典匯入選檔後，以名稱對話框 callback 呼叫可測試的匯入協調函式。
- Modify: `client/locales/dotexpress.pot` — 更新名稱驗證相關 gettext 字串。
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` — 加入台灣繁體中文 Windows 檔名驗證訊息。
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — 編譯更新後的翻譯 catalog。

### Task 1: 共用 Windows 檔名驗證

**Files:**
- Modify: `client/tests/test_document_workspace.py`
- Modify: `client/tests/test_dictionary_manager.py`
- Modify: `client/name_validation.py`

- [ ] **Step 1: 寫入文件名稱的失敗測試**

在 `DocumentWorkspaceTest` 加入下列測試，並把現有 `test_normalize_document_name_rejects_invalid_names` 改成明確的 Windows 案例：

```python
    def test_normalize_document_name_allows_periods(self) -> None:
        for value in ["1.1", "chapter.2", "ver 2.0"]:
            with self.subTest(value=value):
                self.assertEqual(normalize_document_name(value), value)

    def test_normalize_document_name_rejects_windows_invalid_names(self) -> None:
        invalid_values = [
            "",
            " ",
            ".",
            "..",
            "name.",
            "name. ",
            "a<b",
            "a>b",
            "a:b",
            'a"b',
            "a/b",
            "a\\b",
            "a|b",
            "a?b",
            "a*b",
            "a\x00b",
            "a\x1fb",
            "CON",
            "con.txt",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM9.log",
            "LPT1",
            "LPT9.csv",
            "a" * 33,
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_document_name(value)
```

`"name. "` 用來確認去除外部空白後，正規化結果仍會因結尾的點而被拒絕。

- [ ] **Step 2: 寫入字典名稱的失敗測試**

在 `DictionaryManagerTest` 加入：

```python
    def test_normalize_dictionary_name_allows_periods(self) -> None:
        for value in ["1.1", "chapter.2", "ver 2.0"]:
            with self.subTest(value=value):
                self.assertEqual(normalize_dictionary_name(value), value)

    def test_normalize_dictionary_name_rejects_windows_invalid_names(self) -> None:
        invalid_values = [
            "",
            " ",
            ".",
            "..",
            "name.",
            "name. ",
            "a<b",
            "a>b",
            "a:b",
            'a"b',
            "a/b",
            "a\\b",
            "a|b",
            "a?b",
            "a*b",
            "a\x00b",
            "a\x1fb",
            "CON",
            "con.txt",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM9.log",
            "LPT1",
            "LPT9.csv",
            "a" * 33,
            DEFAULT_DICTIONARY_NAME,
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_dictionary_name(value)
```

移除被這兩個新測試取代的舊 `test_normalize_*_rejects_invalid_names`，避免重複案例。

- [ ] **Step 3: 執行測試確認目前會失敗**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_document_workspace.DocumentWorkspaceTest.test_normalize_document_name_allows_periods \
  tests.test_document_workspace.DocumentWorkspaceTest.test_normalize_document_name_rejects_windows_invalid_names \
  tests.test_dictionary_manager.DictionaryManagerTest.test_normalize_dictionary_name_allows_periods \
  tests.test_dictionary_manager.DictionaryManagerTest.test_normalize_dictionary_name_rejects_windows_invalid_names \
  -v
```

Expected: `allows_periods` 因 `.` 被拒絕而 FAIL；Windows 非法字元與保留裝置名稱中的新案例至少一項 FAIL。

- [ ] **Step 4: 實作最小的 Windows 檔名驗證**

將 `client/name_validation.py` 改為：

```python
from __future__ import annotations

MAX_NAME_LENGTH = 32
INVALID_NAME_CHARS = frozenset('<>:"/\\|?*')
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)


def normalize_base_name(name: str, *, reserved_names: set[str] | None = None) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("Name cannot be empty.")
    if len(normalized) > MAX_NAME_LENGTH:
        raise ValueError(f"Name cannot exceed {MAX_NAME_LENGTH} characters.")
    if normalized in {".", ".."}:
        raise ValueError("Name cannot be '.' or '..'.")
    if normalized.endswith((".", " ")):
        raise ValueError("Name cannot end with a period or space.")
    if any(char in INVALID_NAME_CHARS or ord(char) < 32 for char in normalized):
        raise ValueError("Name contains invalid Windows filename characters.")

    device_name = normalized.split(".", 1)[0].upper()
    if device_name in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Name '{normalized}' is reserved by Windows.")
    if reserved_names and normalized.casefold() in {reserved.casefold() for reserved in reserved_names}:
        raise ValueError(f"Name '{normalized}' is reserved.")
    return normalized
```

保留 `strip()` 的既有正規化行為；這表示純粹位於名稱外側的空白會被移除，而移除後以 `.` 結尾的名稱仍會被拒絕。

- [ ] **Step 5: 執行共用名稱測試**

Run:

```bash
cd client
python3 -m unittest tests.test_document_workspace tests.test_dictionary_manager -v
```

Expected: 所有測試 PASS。

- [ ] **Step 6: 提交共用驗證**

```bash
git add \
  client/name_validation.py \
  client/tests/test_document_workspace.py \
  client/tests/test_dictionary_manager.py
git commit -m "feat: allow Windows-valid document and dictionary names"
```

### Task 2: 文件含點號的匯入與 DEP 封包

**Files:**
- Modify: `client/tests/test_document_workspace.py`

- [ ] **Step 1: 加入含點號文字檔匯入測試**

在 `DocumentWorkspaceTest` 加入：

```python
    def test_load_text_document_preserves_periods_in_stem(self) -> None:
        source_path = self.workspace_dir / "1.1.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="1.1", text="hello", braille=None))
```

- [ ] **Step 2: 加入含點號 DEP round-trip 測試**

在 `DocumentWorkspaceTest` 加入：

```python
    def test_document_package_preserves_periods_in_all_names(self) -> None:
        import zipfile

        document = Document(name="1.1", text="source", braille="braille")
        package_path = self.workspace_dir / "1.1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        save_document_package(package_path, document)

        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["1.1.brl", "1.1.txt"])
        self.assertEqual(load_document_package(package_path), document)
```

- [ ] **Step 3: 執行文件測試**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_document_workspace.DocumentWorkspaceTest.test_load_text_document_preserves_periods_in_stem \
  tests.test_document_workspace.DocumentWorkspaceTest.test_document_package_preserves_periods_in_all_names \
  -v
```

Expected: 兩個測試 PASS；`Path.stem` 與現有 DEP 格式不需要 production code 變更。

- [ ] **Step 4: 提交文件回歸測試**

```bash
git add client/tests/test_document_workspace.py
git commit -m "test: cover dotted document names"
```

### Task 3: 名稱對話框共用驗證並支援字典初始值

**Files:**
- Modify: `client/dialog.py`
- Modify: `client/tests/test_dialog_validation.py`

- [ ] **Step 1: 擴充 wx stub 以測試字典對話框初始化**

在 `client/tests/test_dialog_validation.py` 的 import 前 stub 區塊加入可記錄文字欄位狀態的 fake：

```python
class _TextCtrl:
    def __init__(self, _parent):
        self.value = ""
        self.focused = False
        self.selected_all = False

    def SetValue(self, value):
        self.value = value

    def GetValue(self):
        return self.value

    def SetFocus(self):
        self.focused = True

    def SelectAll(self):
        self.selected_all = True
```

為避免複製整套 wx layout stub，將 `DictionaryNameDialog` 中設定初始值的行為抽成方法，並以 `object.__new__` 測試：

```python
    def test_dictionary_dialog_applies_initial_name_and_selects_it(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)
        dialog.name_ctrl = _TextCtrl(None)

        dialog._apply_initial_name("1.1")

        self.assertEqual(dialog.name_ctrl.GetValue(), "1.1")
        self.assertTrue(dialog.name_ctrl.focused)
        self.assertTrue(dialog.name_ctrl.selected_all)
```

- [ ] **Step 2: 加入 UI 驗證與共用 normalizer 一致性的失敗測試**

在 `DialogValidationTextTest` 加入：

```python
    def test_dictionary_name_validation_allows_periods(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)
        self.assertIsNone(dialog._validate_name("1.1"))

    def test_document_name_validation_allows_periods(self) -> None:
        dialog = object.__new__(DocumentNameDialog)
        self.assertIsNone(dialog._validate_name("1.1"))

    def test_name_dialogs_reject_windows_invalid_names(self) -> None:
        dictionary_dialog = object.__new__(DictionaryNameDialog)
        document_dialog = object.__new__(DocumentNameDialog)

        for candidate in ["name.", "CON", "a?b"]:
            with self.subTest(candidate=candidate):
                self.assertIsNotNone(dictionary_dialog._validate_name(candidate))
                self.assertIsNotNone(document_dialog._validate_name(candidate))
```

- [ ] **Step 3: 執行對話框測試確認目前會失敗**

Run:

```bash
cd client
python3 -m unittest tests.test_dialog_validation -v
```

Expected: `1.1` 仍被 UI 拒絕，且 `_apply_initial_name` 尚不存在。

- [ ] **Step 4: 讓字典名稱對話框接受初始值**

將 `DictionaryNameDialog.__init__` 簽章及文字欄位初始化改為：

```python
	def __init__(self, parent: wx.Window | None, initial_name: str = ""):
		super().__init__(parent, title=_("Add Dictionary"))
```

在 `SetSizerAndFit` 後以 helper 套用初始值：

```python
		self.SetSizerAndFit(main_sizer)
		self._apply_initial_name(initial_name)

	def _apply_initial_name(self, initial_name: str) -> None:
		self.name_ctrl.SetValue(initial_name)
		self.name_ctrl.SetFocus()
		self.name_ctrl.SelectAll()
```

刪除原本單獨的 `self.name_ctrl.SetFocus()`。重新命名流程後續也應改由 constructor 傳值，不再直接操作 control。

- [ ] **Step 5: 讓兩個對話框委派 domain normalizer**

將 `DictionaryNameDialog._validate_name` 改為：

```python
	def _validate_name(self, candidate: str) -> str | None:
		if not candidate:
			return _("Please enter the dictionary name.")
		if len(candidate.strip()) > MAX_DICTIONARY_NAME_LENGTH:
			return _("Dictionary name must be 1 to 32 characters.")
		try:
			normalize_dictionary_name(candidate)
		except ValueError:
			return _("Dictionary name is not a valid Windows file name.")
		return None
```

為保留 `default` 的專屬提示，在 `try` 之前加入：

```python
		if candidate.strip().casefold() == DEFAULT_DICTIONARY_NAME.casefold():
			return _('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME)
```

將 `DocumentNameDialog._validate_name` 改為：

```python
	def _validate_name(self, candidate: str) -> str | None:
		if not candidate:
			return _("Please enter the document name.")
		if len(candidate.strip()) > MAX_DICTIONARY_NAME_LENGTH:
			return _("Document name must be 1 to 32 characters.")
		try:
			normalize_document_name(candidate)
		except ValueError:
			return _("Document name is not a valid Windows file name.")
		return None
```

- [ ] **Step 6: 執行對話框測試**

Run:

```bash
cd client
python3 -m unittest tests.test_dialog_validation -v
```

Expected: 所有測試 PASS。

- [ ] **Step 7: 提交對話框行為**

```bash
git add client/dialog.py client/tests/test_dialog_validation.py
git commit -m "feat: support Windows-valid names in dialogs"
```

### Task 4: 字典匯入預填、可修改與取消

**Files:**
- Create: `client/dictionaries/import_flow.py`
- Create: `client/tests/test_dictionary_import_flow.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_dictionary_manager.py`

- [ ] **Step 1: 加入 manager 層含點號目的名稱測試**

在 `DictionaryManagerTest` 加入：

```python
    def test_import_dictionary_preserves_periods_in_name(self) -> None:
        source_path = Path(self._tmpdir.name) / "1.1.csv"
        with source_path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(DEFAULT_HEADER)

        imported_path = import_dictionary(self.dictionary_dir, source_path, "1.1")

        self.assertEqual(imported_path, self.dictionary_dir / "1.1.csv")
        self.assertTrue(imported_path.exists())
```

- [ ] **Step 2: 寫入匯入協調流程的失敗測試**

建立 `client/tests/test_dictionary_import_flow.py`：

```python
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from dictionaries.import_flow import import_dictionary_after_name_prompt


class DictionaryImportFlowTest(unittest.TestCase):
    @patch("dictionaries.import_flow.import_dictionary")
    def test_prefills_source_stem_and_imports_with_edited_name(self, import_mock: Mock) -> None:
        source_path = Path("/incoming/1.1.csv")
        destination = Path("/dictionary/edited.1.csv")
        import_mock.return_value = destination
        prompt_name = Mock(return_value="edited.1")

        result = import_dictionary_after_name_prompt(
            Path("/dictionary"),
            source_path,
            prompt_name=prompt_name,
        )

        prompt_name.assert_called_once_with("1.1")
        import_mock.assert_called_once_with(Path("/dictionary"), source_path, "edited.1")
        self.assertEqual(result, destination)

    @patch("dictionaries.import_flow.import_dictionary")
    def test_cancel_name_prompt_does_not_import(self, import_mock: Mock) -> None:
        prompt_name = Mock(return_value=None)

        result = import_dictionary_after_name_prompt(
            Path("/dictionary"),
            Path("/incoming/1.1.csv"),
            prompt_name=prompt_name,
        )

        self.assertIsNone(result)
        import_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 執行測試確認 module 尚未存在**

Run:

```bash
cd client
python3 -m unittest tests.test_dictionary_import_flow -v
```

Expected: ERROR，訊息包含 `No module named 'dictionaries.import_flow'`。

- [ ] **Step 4: 實作可獨立測試的匯入協調流程**

建立 `client/dictionaries/import_flow.py`：

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from dictionaries.manager import import_dictionary

DictionaryNamePrompt = Callable[[str], str | None]


def import_dictionary_after_name_prompt(
    dictionary_dir: Path | None,
    source_path: Path | str,
    *,
    prompt_name: DictionaryNamePrompt,
) -> Path | None:
    source = Path(source_path)
    dictionary_name = prompt_name(source.stem)
    if dictionary_name is None:
        return None
    return import_dictionary(dictionary_dir, source, dictionary_name)
```

- [ ] **Step 5: 讓 GUI 提供可編輯名稱 callback**

在 `client/gui.py` 匯入：

```python
from dictionaries.import_flow import import_dictionary_after_name_prompt
```

在 `DotExpressFrame` 加入共用名稱提示 helper，並讓新增及重新命名字典也使用此 helper：

```python
	def _prompt_for_dictionary_name(
		self,
		parent: wx.Window,
		*,
		title: str,
		initial_name: str = "",
	) -> str | None:
		with DictionaryNameDialog(parent, initial_name=initial_name) as dialog:
			dialog.SetTitle(title)
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return dialog.get_dictionary_name()
```

將 `add_dictionary` 的原始 `with DictionaryNameDialog(...)` 區塊替換為：

```python
		dictionary_name = self._prompt_for_dictionary_name(
			dialog_parent,
			title=_("Add Dictionary"),
		)
		if dictionary_name is None:
			return None
```

將 `rename_dictionary_from_dialog` 的原始對話框區塊替換為：

```python
		dictionary_name = self._prompt_for_dictionary_name(
			dialog_parent,
			title=_("Rename Dictionary"),
			initial_name=selected_name,
		)
		if dictionary_name is None:
			return None
```

- [ ] **Step 6: 讓字典匯入使用協調流程**

在 `import_dictionary_from_dialog` 中，選檔完成後定義名稱 callback：

```python
		def prompt_name(initial_name: str) -> str | None:
			return self._prompt_for_dictionary_name(
				dialog_parent,
				title=_("Add Dictionary"),
				initial_name=initial_name,
			)
```

以協調函式取代原本直接開啟 `DictionaryNameDialog` 及呼叫 `import_dictionary` 的區塊：

```python
		try:
			path = import_dictionary_after_name_prompt(
				self.dictionary_dir,
				source_path,
				prompt_name=prompt_name,
			)
			if path is None:
				return None
```

保留既有的 `except FileExistsError`、`except ValueError`、`except OSError` 與成功後 state update。刪除 `gui.py` 中不再使用的 `import_dictionary` import。

- [ ] **Step 7: 執行匯入流程測試**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_dictionary_manager.DictionaryManagerTest.test_import_dictionary_preserves_periods_in_name \
  tests.test_dictionary_import_flow \
  -v
```

Expected: 三個測試 PASS；取消名稱對話框時 `import_dictionary` 呼叫次數為 0。

- [ ] **Step 8: 提交字典匯入流程**

```bash
git add \
  client/dictionaries/import_flow.py \
  client/gui.py \
  client/tests/test_dictionary_manager.py \
  client/tests/test_dictionary_import_flow.py
git commit -m "feat: prefill dictionary names during import"
```

### Task 5: 更新 gettext 文案與完整驗證

**Files:**
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: 更新驗證訊息的 template 與台灣繁中翻譯**

移除下列舊 msgid：

```text
Dictionary name cannot contain ".", "/", or "\".
Document name cannot contain ".", "/", or "\".
```

加入新 msgid 與翻譯：

```po
msgid "Dictionary name is not a valid Windows file name."
msgstr "字典名稱不是有效的 Windows 檔名。"

msgid "Document name is not a valid Windows file name."
msgstr "文件名稱不是有效的 Windows 檔名。"
```

在 Windows 執行：

```bat
scripts\generate_pot.bat
```

Expected: `client/locales/dotexpress.pot` 包含兩個新 msgid，且不再把 `.` 列為禁止字元。

- [ ] **Step 2: 編譯並檢查 zh_TW catalog**

Run:

```bash
msgfmt --check client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  -o client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
```

Expected: exit code `0`，沒有格式錯誤。

若目前環境沒有 `msgfmt`，在有 gettext 的 Windows 開發環境執行專案既有翻譯編譯流程；不得提交只更新 `.po`、卻仍保留舊內容的 `.mo`。

- [ ] **Step 3: 執行相關 client 測試**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_document_workspace \
  tests.test_dictionary_manager \
  tests.test_dialog_validation \
  tests.test_dictionary_import_flow \
  -v
```

Expected: 所有測試 PASS。

- [ ] **Step 4: 執行完整 client unittest suite**

Run:

```bash
cd client
python3 -m unittest discover -s tests -v
```

Expected: 所有可在目前平台執行的測試 PASS；依既有條件標記的 Windows/liblouis 測試可顯示 SKIP，但不得出現新的 ERROR 或 FAIL。

- [ ] **Step 5: 在 Windows 手動驗證 wxPython 流程**

以開發版應用程式確認：

1. 匯入 `1.1.txt`，文件清單顯示 `1.1`，儲存後產生 `1.1.dep`。
2. 新增或重新命名文件為 `chapter.2` 成功；輸入 `CON`、`name.` 或 `a?b` 顯示驗證訊息。
3. 選擇匯入 `1.1.csv` 後，「新增字典」文字欄位預填並全選 `1.1`。
4. 將預填名稱改為 `edited.1` 後按 OK，建立 `edited.1.csv`。
5. 再次匯入並在名稱對話框按 Cancel，字典目錄沒有新增或覆寫任何檔案。
6. 使用已存在的名稱按 OK，顯示既有重名錯誤且不覆寫檔案。

- [ ] **Step 6: 提交翻譯與驗證結果**

```bash
git add \
  client/locales/dotexpress.pot \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "fix: update filename validation translations"
```

在 handoff 或 PR 說明中列出 Step 3、Step 4 的精確命令與結果，並註明 Step 5 是否已在 Windows 完成。
