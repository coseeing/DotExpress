# File Menu Import Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將無 config 時的點字字型預設改為 `SimBraille`，新增主視窗 `Alt+O` 直接匯入 TXT，加入頂層 `File` 選單鏡像文件列表右鍵選單，並把共用名稱長度限制從 `16` 提升到 `32`。

**Architecture:** 保留既有文件處理 handler，不重做匯入 / 匯出流程；改以共用的文件選單描述與啟用狀態 helper 同時驅動右鍵選單與新的頂層 `File` 選單。快捷鍵判斷維持在 `ui.shortcuts` 這層，主視窗只負責把 `Alt+O` 導向既有 `on_import_document("txt")`。

**Tech Stack:** Python 3、wxPython、`unittest`、gettext、既有 `config.py` / `documents.workspace` / `ui.action_menu` / `ui.shortcuts`

---

## 檔案配置

- Modify: `client/config.py` — 將 `DEFAULT_BRAILLE_FONT` 從 `default` 改為 `simbraille`。
- Modify: `client/name_validation.py` — 將共用 `MAX_NAME_LENGTH` 從 `16` 提升到 `32`。
- Modify: `client/ui/action_menu.py` — 新增可重用的文件選單結構、格式描述與啟用狀態 helper。
- Modify: `client/ui/shortcuts.py` — 新增 `Alt+O` 對應的純函式快捷鍵判斷。
- Modify: `client/gui.py` — 新增頂層 `File` 選單、共用文件選單綁定、frame 級 `Alt+O`，並讓右鍵選單改讀共用描述。
- Modify: `client/dialog.py` — 更新文件 / 字典名稱驗證文字，從 `16` 改為 `32`。
- Modify: `client/tests/test_config.py` — 補 no-config 時 `get_braille_font()` 回傳 `simbraille` 的測試。
- Modify: `client/tests/test_document_workspace.py` — 更新名稱長度上限測試，並補 32 字元匯入成功案例。
- Modify: `client/tests/test_input_shortcuts.py` — 新增 `Alt+O` 快捷鍵判斷測試。
- Create: `client/tests/test_action_menu.py` — 驗證文件選單順序、子選單結構與 enable/disable 規則。
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` — 新增 `File` 與更新 `1 to 32 characters` 驗證字串。
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — 重新編譯 gettext catalog。
- Reference: `docs/superpowers/specs/2026-06-28-file-menu-import-shortcuts-design.md`

### Task 1: 更新預設值與共用名稱長度規則

**Files:**
- Modify: `client/config.py`
- Modify: `client/name_validation.py`
- Modify: `client/tests/test_config.py`
- Modify: `client/tests/test_document_workspace.py`

- [ ] **Step 1: 先寫設定與名稱限制的失敗測試**

```python
# client/tests/test_config.py
    def test_braille_font_defaults_to_simbraille_when_config_is_missing(self) -> None:
        self.assertEqual(config.get_braille_font(), "simbraille")
```

```python
# client/tests/test_document_workspace.py
    def test_normalize_document_name_accepts_32_characters(self) -> None:
        self.assertEqual(normalize_document_name("a" * 32), "a" * 32)

    def test_normalize_document_name_rejects_more_than_32_characters(self) -> None:
        with self.assertRaises(ValueError):
            normalize_document_name("a" * 33)

    def test_load_text_document_accepts_32_character_stem(self) -> None:
        source_path = self.workspace_dir / f"{'a' * 32}.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="a" * 32, text="hello", braille=None))
```

- [ ] **Step 2: 執行聚焦測試，確認目前行為仍是舊規則**

Run: `cd client && python3 -m unittest tests.test_config tests.test_document_workspace -v`

Expected: FAIL because `get_braille_font()` still defaults to `default`, and `32`-character document names are still rejected by `MAX_NAME_LENGTH = 16`.

- [ ] **Step 3: 以最小修改更新共用預設與名稱限制**

```python
# client/config.py
DEFAULT_BRAILLE_FONT = "simbraille"
```

```python
# client/name_validation.py
MAX_NAME_LENGTH = 32
```

- [ ] **Step 4: 更新既有長度測試資料，改成明確驗證 33 字元失敗**

```python
# client/tests/test_document_workspace.py
    def test_normalize_document_name_rejects_invalid_names(self) -> None:
        for value in ["", " ", ".", "a/b", r"a\\b", "a" * 33]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_document_name(value)
```

- [ ] **Step 5: 執行設定與文件工作區測試**

Run: `cd client && python3 -m unittest tests.test_config tests.test_document_workspace -v`

Expected: PASS.

- [ ] **Step 6: 提交共用預設與名稱限制變更**

```bash
git add client/config.py client/name_validation.py client/tests/test_config.py client/tests/test_document_workspace.py
git commit -m "feat: widen shared name limits and default braille font"
```

### Task 2: 建立可共用的文件選單描述與快捷鍵判斷

**Files:**
- Modify: `client/ui/action_menu.py`
- Modify: `client/ui/shortcuts.py`
- Create: `client/tests/test_action_menu.py`
- Modify: `client/tests/test_input_shortcuts.py`

- [ ] **Step 1: 寫入文件選單結構與 `Alt+O` 的失敗測試**

```python
# client/tests/test_action_menu.py
import unittest

from ui.action_menu import (
    get_document_menu_items,
    get_document_menu_enabled_state,
)


class ActionMenuTest(unittest.TestCase):
    def test_document_menu_items_match_required_order_and_formats(self) -> None:
        self.assertEqual(
            get_document_menu_items(),
            [
                ("command", "Open"),
                ("command", "Delete"),
                ("command", "Delete All"),
                ("command", "Add"),
                ("command", "Rename"),
                ("submenu", "Import", ["DEP", "TXT"]),
                ("submenu", "Export", ["DEP", "BRL"]),
                ("submenu", "Export All", ["DEP", "BRL"]),
            ],
        )

    def test_document_menu_enabled_state_matches_selection_rules(self) -> None:
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=False, has_documents=False),
            {
                "Open": False,
                "Delete": False,
                "Delete All": False,
                "Add": True,
                "Rename": False,
                "Import": True,
                "Export": False,
                "Export All": False,
            },
        )
        self.assertEqual(
            get_document_menu_enabled_state(has_selection=True, has_documents=True),
            {
                "Open": True,
                "Delete": True,
                "Delete All": True,
                "Add": True,
                "Rename": True,
                "Import": True,
                "Export": True,
                "Export All": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
```

```python
# client/tests/test_input_shortcuts.py
from ui.shortcuts import is_document_import_txt_shortcut

    def test_alt_o_shortcut_for_txt_import(self) -> None:
        cases = [
            ("alt o", {"key_code": 79, "alt_down": True}, True),
            ("plain o", {"key_code": 79, "alt_down": False}, False),
            ("alt other key", {"key_code": 80, "alt_down": True}, False),
        ]

        for label, kwargs, expected in cases:
            with self.subTest(label=label):
                self.assertEqual(is_document_import_txt_shortcut(**kwargs), expected)
```

- [ ] **Step 2: 執行測試，確認 helper 尚未存在**

Run: `cd client && python3 -m unittest tests.test_action_menu tests.test_input_shortcuts -v`

Expected: FAIL with `ImportError` / `AttributeError` because `get_document_menu_items`, `get_document_menu_enabled_state`, and `is_document_import_txt_shortcut` do not exist yet.

- [ ] **Step 3: 在 `ui.action_menu.py` 新增共用文件選單描述與啟用狀態 helper**

```python
# client/ui/action_menu.py
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentMenuCommand:
    kind: str
    label: str
    formats: tuple[str, ...] = ()


DOCUMENT_MENU_ITEMS = (
    DocumentMenuCommand("command", "Open"),
    DocumentMenuCommand("command", "Delete"),
    DocumentMenuCommand("command", "Delete All"),
    DocumentMenuCommand("command", "Add"),
    DocumentMenuCommand("command", "Rename"),
    DocumentMenuCommand("submenu", "Import", ("DEP", "TXT")),
    DocumentMenuCommand("submenu", "Export", ("DEP", "BRL")),
    DocumentMenuCommand("submenu", "Export All", ("DEP", "BRL")),
)


def get_document_menu_items() -> list[tuple[str, str] | tuple[str, str, list[str]]]:
    items: list[tuple[str, str] | tuple[str, str, list[str]]] = []
    for item in DOCUMENT_MENU_ITEMS:
        if item.kind == "submenu":
            items.append((item.kind, item.label, list(item.formats)))
        else:
            items.append((item.kind, item.label))
    return items


def get_document_menu_enabled_state(
    *,
    has_selection: bool,
    has_documents: bool,
) -> dict[str, bool]:
    return {
        "Open": has_selection,
        "Delete": has_selection,
        "Delete All": has_documents,
        "Add": True,
        "Rename": has_selection,
        "Import": True,
        "Export": has_selection,
        "Export All": has_documents,
    }
```

- [ ] **Step 4: 在 `ui.shortcuts.py` 加入 `Alt+O` 判斷函式**

```python
# client/ui/shortcuts.py
O_KEY_CODE = 79


def is_document_import_txt_shortcut(key_code: int, alt_down: bool) -> bool:
    return alt_down and key_code == O_KEY_CODE
```

- [ ] **Step 5: 執行共用 helper 與快捷鍵測試**

Run: `cd client && python3 -m unittest tests.test_action_menu tests.test_input_shortcuts -v`

Expected: PASS.

- [ ] **Step 6: 提交文件選單 helper 與快捷鍵判斷**

```bash
git add client/ui/action_menu.py client/ui/shortcuts.py client/tests/test_action_menu.py client/tests/test_input_shortcuts.py
git commit -m "refactor: share document menu definitions"
```

### Task 3: 將共用文件選單與 `Alt+O` 串接到主視窗

**Files:**
- Modify: `client/gui.py`
- Reference: `client/ui/action_menu.py`
- Reference: `client/ui/shortcuts.py`

- [ ] **Step 1: 先寫 GUI 層的純結構測試，避免直接測 wx 視窗物件**

```python
# client/tests/test_action_menu.py
from ui.action_menu import get_document_menu_items

    def test_document_menu_includes_import_txt_entry_for_accelerator_target(self) -> None:
        import_item = next(item for item in get_document_menu_items() if item[1] == "Import")
        self.assertEqual(import_item, ("submenu", "Import", ["DEP", "TXT"]))
```

```python
# client/tests/test_translation_menu.py
import unittest

from ui.translation_menu import get_translation_menu_items


class TranslationMenuTest(unittest.TestCase):
    def test_menu_items_match_required_fixed_order(self) -> None:
        self.assertEqual(
            get_translation_menu_items(),
            [
                ("convert", "Convert"),
                ("settings", "Translation Settings..."),
                ("tables", "Translation Tables Setting..."),
                ("dictionaries", "Dictionary Management..."),
            ],
        )
```

Expected: no new failure from this step by itself; it locks the structure before changing `gui.py`.

- [ ] **Step 2: 新增 `File` 選單建構 helper，並將右鍵選單改為共用定義**

```python
# client/gui.py
from ui.action_menu import (
    DOCUMENT_MENU_ITEMS,
    get_document_menu_enabled_state,
)
from ui.shortcuts import is_document_import_txt_shortcut
```

```python
# client/gui.py
    def _append_document_menu_items(
        self,
        menu: wx.Menu,
    ) -> tuple[dict[str, wx.MenuItem], dict[str, wx.MenuItem]]:
        menu_items: dict[str, wx.MenuItem] = {}
        format_items: dict[str, wx.MenuItem] = {}
        for item in DOCUMENT_MENU_ITEMS:
            if item.kind == "submenu":
                submenu = wx.Menu()
                menu_items[item.label] = menu.AppendSubMenu(submenu, _(item.label))
                action_key = item.label.casefold().replace(" ", "-")
                for format_label in item.formats:
                    format_items[f"{action_key}:{format_label.lower()}"] = submenu.Append(
                        wx.ID_ANY,
                        _(format_label),
                    )
            else:
                menu_items[item.label] = menu.Append(wx.ID_ANY, _(item.label))
        return menu_items, format_items

    def _bind_document_menu_handlers(
        self,
        menu: wx.Menu,
        menu_items: dict[str, wx.MenuItem],
        format_items: dict[str, wx.MenuItem],
    ) -> None:
        menu.Bind(wx.EVT_MENU, self.on_open_document, menu_items["Open"])
        menu.Bind(wx.EVT_MENU, self.on_delete_document, menu_items["Delete"])
        menu.Bind(wx.EVT_MENU, self.on_delete_all_documents, menu_items["Delete All"])
        menu.Bind(wx.EVT_MENU, self.on_add_document, menu_items["Add"])
        menu.Bind(wx.EVT_MENU, self.on_rename_document, menu_items["Rename"])
        for key, item in format_items.items():
            action, format_key = key.split(":")
            if action == "import":
                menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_import_document(fmt), item)
            elif action == "export":
                menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_document(fmt), item)
            elif action == "export-all":
                menu.Bind(wx.EVT_MENU, lambda _evt, fmt=format_key: self.on_export_all_documents(fmt), item)

    def _apply_document_menu_enabled_state(self, menu_items: dict[str, wx.MenuItem]) -> None:
        state = get_document_menu_enabled_state(
            has_selection=self._get_selected_document() is not None,
            has_documents=bool(self.documents),
        )
        for label, enabled in state.items():
            menu_items[label].Enable(enabled)
```

- [ ] **Step 3: 在主選單列加入頂層 `File` 選單**

```python
# client/gui.py
    def _create_menu_bar(self) -> wx.MenuBar:
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        file_menu_items, file_format_items = self._append_document_menu_items(file_menu)
        self._bind_document_menu_handlers(file_menu, file_menu_items, file_format_items)
        self._file_menu_items = file_menu_items
        menu_bar.Append(file_menu, _("File"))

        translation_menu = wx.Menu()
        ...
```

- [ ] **Step 4: 讓文件列表右鍵選單改讀同一份共用 helper**

```python
# client/gui.py
    def on_document_context_menu(self, event: wx.ContextMenuEvent) -> None:
        ...
        menu = wx.Menu()
        menu_items, format_items = self._append_document_menu_items(menu)
        self._apply_document_menu_enabled_state(menu_items)
        self._bind_document_menu_handlers(menu, menu_items, format_items)
        ...
```

- [ ] **Step 5: 在 `on_char_hook` 加上 frame 級 `Alt+O`**

```python
# client/gui.py
    def on_char_hook(self, event: wx.KeyEvent) -> None:
        if is_document_import_txt_shortcut(event.GetKeyCode(), event.AltDown()):
            self.on_import_document("txt")
            return

        step = is_section_navigation_shortcut(event.GetKeyCode(), event.ShiftDown())
        if step == 0:
            event.Skip()
            return
        ...
```

- [ ] **Step 6: 讓 busy state 同步停用頂層 `File` 與 `Translation` 選單**

```python
# client/gui.py
    def _set_conversion_busy(self, busy: bool):
        menu_bar = self.GetMenuBar()
        if menu_bar is not None:
            menu_bar.EnableTop(0, not busy)
            menu_bar.EnableTop(1, not busy)
        self.document_list.Enable(not busy)
        self.input_txt.Enable(not busy)
```

- [ ] **Step 7: 執行主視窗相關測試與既有選單測試**

Run: `cd client && python3 -m unittest tests.test_action_menu tests.test_translation_menu tests.test_input_shortcuts tests.test_document_workspace -v`

Expected: PASS.

- [ ] **Step 8: 提交主視窗文件選單與 `Alt+O` 串接**

```bash
git add client/gui.py client/tests/test_action_menu.py client/tests/test_translation_menu.py client/tests/test_input_shortcuts.py
git commit -m "feat: add file menu and txt import shortcut"
```

### Task 4: 更新驗證文字、本地化與完整驗證

**Files:**
- Modify: `client/dialog.py`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: 先寫出會失敗的名稱驗證訊息測試**

```python
# client/tests/test_action_menu.py
import unittest

from dialog import DictionaryNameDialog, DocumentNameDialog


class DialogValidationTextTest(unittest.TestCase):
    def test_document_name_validation_mentions_32_characters(self) -> None:
        dialog = DocumentNameDialog(None, "Rename Document")
        try:
            self.assertEqual(
                dialog._validate_name("a" * 33),
                "Document name must be 1 to 32 characters.",
            )
        finally:
            dialog.Destroy()

    def test_dictionary_name_validation_mentions_32_characters(self) -> None:
        dialog = DictionaryNameDialog(None)
        try:
            self.assertEqual(
                dialog._validate_name("a" * 33),
                "Dictionary name must be 1 to 32 characters.",
            )
        finally:
            dialog.Destroy()
```

- [ ] **Step 2: 執行測試，確認仍使用舊的 16 字元訊息**

Run: `cd client && python3 -m unittest tests.test_action_menu -v`

Expected: FAIL because `dialog.py` still returns `1 to 16 characters.` messages.

- [ ] **Step 3: 更新 `dialog.py` 驗證訊息與 `File` 本地化字串**

```python
# client/dialog.py
        if len(candidate) > MAX_DICTIONARY_NAME_LENGTH:
            return _("Dictionary name must be 1 to 32 characters.")
```

```python
# client/dialog.py
        if len(candidate) > MAX_DICTIONARY_NAME_LENGTH:
            return _("Document name must be 1 to 32 characters.")
```

```po
# client/locales/zh_TW/LC_MESSAGES/dotexpress.po
msgid "File"
msgstr "檔案"

msgid "Dictionary name must be 1 to 32 characters."
msgstr "字典名稱長度必須介於 1 到 32 個字元。"

msgid "Document name must be 1 to 32 characters."
msgstr "文件名稱長度必須介於 1 到 32 個字元。"
```

- [ ] **Step 4: 使用純 Python 重新編譯 gettext catalog**

Run:

```bash
python3 - <<'PY'
from __future__ import annotations

import ast
import re
import struct
from pathlib import Path

po_path = Path("client/locales/zh_TW/LC_MESSAGES/dotexpress.po")
mo_path = Path("client/locales/zh_TW/LC_MESSAGES/dotexpress.mo")

entries: list[tuple[str, str]] = []
msgid: str | None = None
msgstr: str | None = None
state: str | None = None

pattern = re.compile(r'^(msgid|msgstr)\s+(".*")$')

for raw_line in po_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        if msgid is not None and msgstr is not None:
            entries.append((msgid, msgstr))
            msgid = None
            msgstr = None
            state = None
        continue

    match = pattern.match(line)
    if match:
        state = match.group(1)
        value = ast.literal_eval(match.group(2))
        if state == "msgid":
            msgid = value
        else:
            msgstr = value
        continue

    if line.startswith('"'):
        value = ast.literal_eval(line)
        if state == "msgid" and msgid is not None:
            msgid += value
        elif state == "msgstr" and msgstr is not None:
            msgstr += value

if msgid is not None and msgstr is not None:
    entries.append((msgid, msgstr))

entries.sort(key=lambda item: item[0])
ids = [item[0].encode("utf-8") for item in entries]
strs = [item[1].encode("utf-8") for item in entries]

keystart = 7 * 4 + 16 * len(entries)
valuestart = keystart + sum(len(msgid_bytes) + 1 for msgid_bytes in ids)

key_offset = keystart
value_offset = valuestart
key_table: list[tuple[int, int]] = []
value_table: list[tuple[int, int]] = []

for msgid_bytes, msgstr_bytes in zip(ids, strs):
    key_table.append((len(msgid_bytes), key_offset))
    value_table.append((len(msgstr_bytes), value_offset))
    key_offset += len(msgid_bytes) + 1
    value_offset += len(msgstr_bytes) + 1

with mo_path.open("wb") as mo_file:
    mo_file.write(struct.pack("Iiiiiii", 0x950412DE, 0, len(entries), 28, 28 + len(entries) * 8, 0, 0))
    for length, offset in key_table:
        mo_file.write(struct.pack("ii", length, offset))
    for length, offset in value_table:
        mo_file.write(struct.pack("ii", length, offset))
    for msgid_bytes in ids:
        mo_file.write(msgid_bytes + b"\0")
    for msgstr_bytes in strs:
        mo_file.write(msgstr_bytes + b"\0")
PY
```

Expected: exit code `0`, and `dotexpress.mo` timestamp updates.

- [ ] **Step 5: 執行完整 client 單元測試**

Run: `cd client && python3 -m unittest discover -s tests -v`

Expected: PASS for all runnable tests, with only the existing platform-limited liblouis cases reported as skips if the current environment lacks those runtime requirements.

- [ ] **Step 6: 提交本地化與最終驗證**

```bash
git add client/dialog.py client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo client/tests/test_action_menu.py
git commit -m "chore: localize file menu and 32-char validation"
```

## 自我檢查

- Spec coverage:
  - `SimBraille` no-config 預設：Task 1
  - `Alt+O` 直接 TXT 匯入：Task 2、Task 3
  - 頂層 `File` 選單鏡像文件列表右鍵選單：Task 2、Task 3
  - 名稱限制 `16 -> 32`：Task 1、Task 4
  - 本地化更新：Task 4
- Placeholder scan:
  - 已避免 `TBD` / `TODO` / 「自行處理」類描述
  - 每個代碼步驟都給了具體片段與指令
- Type consistency:
  - 共用文件選單 API 使用 `DOCUMENT_MENU_ITEMS`、`get_document_menu_items()`、`get_document_menu_enabled_state()`
  - 快捷鍵 API 使用 `is_document_import_txt_shortcut()`
  - GUI 端固定走既有 `on_import_document("txt")`

## 執行交接

Plan complete and saved to `docs/superpowers/plans/2026-06-28-file-menu-import-shortcuts-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
