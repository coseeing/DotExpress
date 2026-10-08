# 匯出與選單契約（P1-2）設計

## 目標

讓「文件格式 registry」與「文件選單 descriptor」成為描述匯出格式與文件選單項目的唯一來源。目前 `gui.py` 在四個地方重複這些資訊或繞過它們。本任務是 `storage/refactor.md`（6.2 節）路線圖的 P1-2，涵蓋 O-1、O-2（3.2 節）、L-3（3.3 節）、P-4（4.2 節），以及 P0 階段審查（`docs/superpowers/history/2026-10-08-01-refactor-p0/review_task.md`）的 M-4。

具體來說：

- **單一 writer 契約（O-2、L-3、P-4）。** 每個匯出 writer 都接收 `(path, document, context: ExportContext)`。`ExportContext` 攜帶 dual-view 結果。`gui._write_export_document` 以相同方式呼叫所有 writer，不再判斷 `"html"`。
- **匯出 wildcard 與 Export 子選單改由 registry 產生（O-2、P-4）。** `DocumentFormatDescriptor` 新增 `export_wildcard` 與 `export_label`。存檔對話框的 wildcard 來自 `formats.build_export_wildcard(descriptor, _)`。Export 與 Export All 子選單由 `formats.get_exportable_formats()` 建立。這取代了 `gui._get_export_wildcard` 的硬編碼 dict、`gui.py` 的三個 `*_WILDCARD` 常數，以及 `ui/action_menu.py` 中兩份硬編碼的格式 tuple。
- **選單以 action 為 key（O-1）。** `DocumentMenuItem` 新增 `enabled_when`。`get_document_menu_enabled_state` 回傳由 descriptor 推導的 `{action: bool}`。新增不依賴 wx 的 `ui/menu_builder.py`，依 descriptor 與 `{action: handler}` 對照表建立並綁定文件選單，File 選單與文件清單的右鍵選單都使用它。程式不再以英文 label 查找選單項目。
- **可翻譯字串在定義處標記（M-4）。** 刪除 `gui._MENU_TRANSLATION_MARKERS`。每個 label 在定義處以 `N_()` 包起來，擷取出的 msgid 集合只少了四個沒有地方顯示的孤立匯入篩選字串（357 變成 353）。

這是保持行為不變的重構。選單順序、label、巢狀結構、啟用狀態、handler、快速鍵、對話框標題與 wildcard，以及每個匯出檔案的位元組內容都不變。沒有任何使用者可見字串改變，`client/locales/` 下也不手動修改任何檔案。

本 spec 已納入實作計畫（`docs/superpowers/plans/2026-10-08-p1-2-export-menu-contracts.md` 的「Spec Corrections and Refinements」一節）的更正與細化：還有一個測試釘住標記 tuple、記錄用 fake 集中在 `tests/menu_recording.py`、特性測試共 11 個、`gui` 不再 import `get_document_menu_descriptors`、建構器的 `ValueError` 文字固定、`ExportContext` 有自己的測試，以及 zh_TW label 測試會略過註解與 obsolete 條目。

## 現況（2026-10-08 於 `refactor/p1-2-export-menu-contracts` 驗證，HEAD `029a86e`，已合併 P0-1..P0-6 與 P1-1）

縮排：`gui.py` 與 `dialog.py` 用 tab（`gui.py` 的 import 區塊有幾行 4 空白的續行，維持原樣）。`documents/formats.py`、`ui/action_menu.py`、`ui/translation_menu.py`、`conversion/preprocessing/user_script.py` 以及會動到的測試用 4 空白。新增的 `ui/menu_builder.py` 與 `tests/test_menu_builder.py` 跟 `ui/` 其他檔案一樣用 4 空白。

### 匯出路徑

| 步驟 | 位置 | 行為 |
| --- | --- | --- |
| 選單或快速鍵 | `gui.on_export_document(format_key)` 1117、`gui.on_export_all_documents(format_key)` 1126；輸出編輯區的 Ctrl+S（`gui.on_output_text_key_down` 1163-1171）呼叫 `_export_document_with_dialog(document, get_format("brl").key)` | 先儲存開啟中的文件，再匯出。 |
| 單一匯出對話框 | `gui._export_document_with_dialog` 730-765 | `wx.FileDialog(self, _("Export Document"), defaultFile=f"{name}{ext}", wildcard=self._get_export_wildcard(key), style=wx.FD_SAVE \| wx.FD_OVERWRITE_PROMPT)`。選擇的路徑副檔名（不分大小寫比較）不是格式副檔名時，改用 `with_suffix(ext)`。若 `document.braille is None`，**所有**格式（不只 `requires_braille` 的格式）都會先轉換，之後才執行 `_continue_single_export`。 |
| Export All | `gui.on_export_all_documents` 1126-1139、`_export_next_document` 1278-1321 | `wx.DirDialog`、覆寫確認，然後每個 `wx.CallAfter` 步驟處理一份文件。每個目標路徑為 `dir / f"{name}{descriptor.extension}"`。 |
| 寫出 | `gui._write_export_document` 1217-1228 | `get_format(key)`。格式不可匯出或沒有 writer 時丟出 `ValueError('Unsupported export format: "<key>".')`。**特例：** `"html"` 呼叫 `writer(path, document, dual_view_results=self._dual_view_results_by_document.get(document.name, ()))`，其他格式呼叫 `writer(path, document)`。 |
| Registry writers | `documents/formats.py` 73-93 | `_write_dep(path, document)` 回傳 `save_document_package(path, document, include_pending_metadata=False)`（`Path`）。`_write_brl(path, document)` 回傳 `export_document_brl(...)`（`Path`）。`_write_html(path, document, *, dual_view_results=())` 不使用 document，回傳 `Path(path).write_text(render_dual_view_html(build_dual_view_model(dual_view_results)), encoding="utf-8")`，也就是一個 `int`。沒有人讀取回傳值。`_write_html` 不會建立不存在的上層目錄，DEP 與 BRL writer 會。 |
| Descriptor 型別 | `documents/formats.py` 21-30 | `loader: Callable[[Path \| str], object] \| None` 與 `writer: Callable[[Path \| str, object], object] \| None`。實際的 writer 契約不在型別上（L-3）。 |

路線圖列出的 `documents/workspace.py:184-203` `batch_export_documents_to_folder` 已在 P0-3 刪除，`documents/workspace.py` 沒有需要修改的地方。

`DocumentFormatDescriptor.requires_braille` 在 production 沒有讀取者。不論格式為何，只要文件 `braille is None`，`gui` 就會先轉換再匯出。本任務保留此行為，不碰這個欄位。

### 匯出 wildcard

- `gui.py:125-127`：`DEP_WILDCARD = "DotExpress files (*.dep)|*.dep"`、`BRL_WILDCARD = "Braille files (*.brl)|*.brl"`、`HTML_WILDCARD = "HTML files (*.html)|*.html"`。
- `gui.py:591-592, 686-697`：`_get_dep_wildcard`、`_get_brl_wildcard`、`_get_html_wildcard` 各自回傳 `_(<常數>)`。`_get_export_wildcard(key)` 從硬編碼的 `{"dep", "brl", "html"}` dict 中挑一個。這些方法沒有其他呼叫者。
- DEP 與 BRL 字串是 msgid（透過 `_MENU_TRANSLATION_MARKERS`），有 zh_TW 翻譯。`"HTML files (*.html)|*.html"` **不是** msgid：它只透過變數傳給 `_()`，`dotexpress.pot`/`.po` 都沒有它，執行時 `_()` 原樣回傳。
- Registry 的 `wildcard_label`（`"DEP"`、`"BRL"`、`"HTML"`…）是**匯入** wildcard 的短標籤（`build_import_wildcard`，產生 `"DEP (*.dep)|*.dep|..."`），匯出對話框不使用它。匯出字串是不同的文字，若從 `wildcard_label` 推導，就會改變使用者看到的內容與 msgid。
- 匯入（`gui.on_import_document` 1082-1116）已經使用 registry（`build_import_wildcard(_)`、`get_import_filters()[filter_index].key`、`ALL_SUPPORTED_FILTER_INDEX`），本任務不更動。

### 文件選單

- Descriptor（`ui/action_menu.py:6-33`）：`DocumentMenuItem(kind, label, action="", formats=())`，順序為 Open（`open`）、Delete（`delete`）、Delete All（`delete_all`）、Add（`add`）、Rename（`rename`）、Import（`import`）、Export（`export`，子選單）、Export All（`export_all`，子選單）。兩個子選單都列出 `(("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`，硬編碼兩次，順序與 `get_exportable_formats()` 相同。
- 啟用狀態（`ui/action_menu.py:40-50`）：回傳以**英文 label** 為 key 的 dict：Open、Delete、Rename、Export 跟隨 `has_selection`；Delete All、Export All 跟隨 `has_documents`；Add、Import 永遠啟用。
- 建立（`gui._create_document_menu` 391-396、`_append_document_menu_items` 398-414）：`menu = wx.Menu()`。依序處理每個 descriptor：command 變成 `menu.Append(wx.ID_ANY, _(label))`；submenu 變成 `submenu = wx.Menu()`，接著 `menu.AppendSubMenu(submenu, _(label))`，再對每個格式 `submenu.Append(wx.ID_ANY, _(format_label))`。頂層項目以 **label** 存放，子選單項目以 `action` 再以 `format_key.casefold()` 存放。
- 綁定（`gui._bind_document_menu_handlers` 416-431）：每個項目（含子選單項目）都在**頂層** menu 上 `menu.Bind(wx.EVT_MENU, handler, item)`，順序為 Open、Delete、Delete All、Add、Rename、Import（以 `menu_items["Open"]` 等方式查找），接著每個 Export 格式（`lambda _evt, fmt=key: self.on_export_document(fmt)`），再接著每個 Export All 格式（`self.on_export_all_documents(fmt)`）。`DocumentMenuItem.action` 只用來找子選單項目。label 改名會讓 `menu_items["..."]` 丟出 `KeyError`；狀態 dict 中缺少的 label 會被 `_sync_document_menu_state` 靜默略過。
- 狀態（`gui._sync_document_menu_state` 433-445）：使用傳入的項目，或 `self._document_menu_items`。沒有項目或 frame 尚未初始化時提早返回。`document_list` 存在之前 `has_selection` 為 `False`。之後對狀態 dict 中的每個 label 呼叫 `item.Enable(enabled)`（dict 順序 = 上述順序）。init 順序的防禦（`hasattr(self, "documents")`、`"document_list" in self.__dict__`）屬於 P1-3，維持原樣。
- 選單列（`gui._create_menu_bar` 362-389）：File（文件選單）、Translation（`ui/translation_menu.get_translation_menu_items()`：Convert、Dual View、Text Processing、Dictionary Management...、Settings，透過 `self.Bind` 綁在 frame 上）、Help（Coseeing Website 用 `wx.ID_ANY`、About 用 `wx.ID_ABOUT`）。頂層標題為 `_("File")`、`_("Translation")`、`_("Help")`。
- 右鍵選單，也就是 AGENTS.md 所說的「Actions popup」（`gui.on_document_context_menu` 941-961）：先 hit-test，選取或清除選取，以相同的 `_append_document_menu_items`、`_bind_document_menu_handlers`、`_sync_document_menu_state` 呼叫建立新的 `wx.Menu()`，呼叫 `document_list.PopupMenu(menu, position)`，最後 `menu.Destroy()`。AGENTS.md 要求檢查的「ordering helpers」就是 descriptor 順序與 registry 順序。舊的 Actions 按鈕 helper（`build_actions_button_label`、`get_actions_menu_position`）已在 P0-3 刪除。
- 加速鍵：沒有任何選單 label 帶 `\t` 加速鍵或 `&` 助記符，也沒有 `wx.AcceleratorTable`。鍵盤快速鍵都是使用 `ui/shortcuts.py` 的按鍵 handler：Ctrl+Enter 轉換、輸出編輯區的 Ctrl+S 匯出 BRL、Ctrl+O 匯入、Ctrl+Tab 與 Ctrl+PageUp/PageDown 切換文件、F2 改名、Delete 刪除、F6/Shift+F6 切換區塊。它們都不經過選單，所以本任務不影響它們。Ctrl+S 會進入 `_export_document_with_dialog`，測試涵蓋了這條路徑。
- 不在範圍內：`gui._set_conversion_busy`（1370-1378）以翻譯後的標題 `FindMenu(_("File"))` 查找選單（refactor.md 5.3 節）。它屬於轉換忙碌狀態，歸 P1-4（`ConversionPresenter`）。

### 翻譯標記（`gui.py:131-181`）

`_MENU_TRANSLATION_MARKERS` 是 48 個沒有人讀取的 `N_("...")` 呼叫組成的 tuple，唯一用途是讓 `xgettext --keyword=_ --keyword=N_`（`scripts/generate-pot.bat`）看得到透過變數翻譯的字串。以 AST 掃描 `client/`（排除 `tests/` 與 `.venv/`）中所有 `_()`/`N_()` 字面值呼叫與所有裸字串常數，結果如下：

| 分組 | 標記 | 目前的其他擷取位置 | 處理方式 |
| --- | --- | --- | --- |
| A. 已在別處擷取（23） | Add、Edit、Delete、Import、Export、Dual View、Rename、Default、Braille Font、SimBraille、Translation、"No conversion data is available for this document."、Text Processing、Text Processing Python Code、"Unable to open text processing script: {error}"、"Unable to save text processing script: {error}"、"Text processing failed: {error}"、Confirm Delete Dictionary、`Do you want to delete dictionary "{name}"?`、Rename Dictionary、Help、Coseeing Website、About DotExpress | `dialog.py`、`settings/dialogs.py`、`dictionaries/presenter.py` 或 `gui.py` 中的字面值 `_()` 呼叫 | 刪除標記，msgid 仍在。 |
| B. 只靠標記擷取（21） | Open、Delete All、Export All（`ui/action_menu.py`）；Package DEP、Braille BRL、Dual View HTML（`ui/action_menu.py` 各出現兩次，改放到 `documents/formats.py`）；DEP、DOCX、EPUB、PDF、TXT、BRL（`documents/formats.py` 的 `wildcard_label`）；All Supported Files（`documents/formats.py:200, 205`）；Convert、Settings、Dictionary Management...（`ui/translation_menu.py`）；`conversion/preprocessing/user_script.py:39, 48` 的兩個 `ValueError` 訊息（經 `settings/dialogs.py:148` 的 `_(str(error))` 顯示）；"CSV files (*.csv)\|*.csv"（`dialog.py:28` `CSV_WILDCARD`）；"DotExpress files (*.dep)\|*.dep" 與 "Braille files (*.brl)\|*.brl"（`gui.py:125-126`，改放到 `documents/formats.py`） | 只有定義處的裸字串 | 在定義處以 `N_()` 包起來。 |
| C. 已無定義處（4） | "Text files (*.txt)\|*.txt"、"PDF files (*.pdf)\|*.pdf"、"Word documents (*.docx)\|*.docx"、"EPUB books (*.epub)\|*.epub" | 無。這些原本是 P0-3 刪除的 `IMPORT_WILDCARDS`，沒有地方顯示它們。 | 刪除。見下方「孤立的 msgid」。 |

AST 掃描工具（`p06impl/tools/msgid_scan.py`，已複製到 session scratchpad 的 `p12/tools/msgid_scan.py`，基線存為 `p12/base_msgids.json`）在原始碼中找到 357 個 msgid，`client/locales/dotexpress.pot` 也是 357 個，兩個集合相等。在 scratch 複本上依下文方式標記的 dry run 得到 353：`.pot` 只多出 C 組那四個字串，其他完全相同。

### 釘住現狀的測試

- `tests/test_action_menu.py`：以 label 為 key 的啟用狀態 dict（4 個測試），以及 Export/Export All 的 `formats` tuple。
- `tests/test_document_formats.py`：`test_html_writer_renders_cached_dual_view_results_as_utf8` 以 keyword 參數 `dual_view_results=` 呼叫 HTML writer。
- `tests/test_gui_document_flows.py`：`test_write_export_document_uses_registry_writer`（斷言 `writer(path, document)`）、`test_write_html_export_document_passes_cached_dual_view_results`（斷言 `dual_view_results=` keyword 參數）、`test_sync_document_menu_state_before_document_list_exists`（以 label 為 key 的項目），以及 `test_dead_frame_helpers_are_removed`，其最後兩行斷言 `gui.DEP_WILDCARD` 與 `BrailleFrame._get_brl_wildcard` **仍存在**。這兩行是 P0-3 加入的「刻意保留」守門，本任務會刪除這兩個名稱。
- `tests/test_i18n.py::SharedSetupConsumerTest`：`gui.py` 必須從 `i18n` 恰好 import `{"N_", "_", "resource_path"}`，`dialog.py` 恰好 `{"_"}`。
- `tests/test_i18n.py::ExtractionMarkerTest::test_gui_menu_translation_markers_use_n_`（P0-5）：解析 `gui.py`，斷言 `_MENU_TRANSLATION_MARKERS` 存在，且是恰好 48 個 `N_()` 呼叫組成的 tuple。刪除這個 tuple（步驟 6）會讓它失敗，所以步驟 6 會替換它（見「更新的測試」）。
- `tests/test_removed_dead_code.py`：要求 `action_menu.get_document_menu_descriptors`、`action_menu.get_document_menu_enabled_state`、`formats.get_exportable_formats`、`formats.get_import_filter_labels` 存在。四者都保留。

### 基線

HEAD `029a86e` 完整測試（Linux venv）：575 個測試，`failures=1`（已知的 P2-5 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`），`skipped=7`。聚焦模組（`test_document_formats`、`test_action_menu`、`test_gui_document_flows`、`test_i18n`、`test_removed_dead_code`、`test_translation_menu`、`test_export_results`、`test_user_preprocessing_script`）共 118 個測試，全部通過。

## 設計

### 格式 registry（`documents/formats.py`）

```python
@dataclass(frozen=True)
class ExportContext:
    """What an export writer may need besides the document itself."""
    dual_view_results: tuple[object, ...] = ()

DocumentLoader = Callable[[Path | str], "Document"]
DocumentWriter = Callable[[Path | str, "Document", ExportContext], Path]

@dataclass(frozen=True)
class DocumentFormatDescriptor:
    key: str
    extension: str
    wildcard_label: str              # import-wildcard label, unchanged
    loader: DocumentLoader | None
    writer: DocumentWriter | None
    requires_braille: bool           # unchanged, still unread by gui
    importable: bool
    exportable: bool
    export_wildcard: str | None = None   # full single-format save-dialog filter, untranslated
    export_label: str | None = None      # Export / Export All submenu label, untranslated
```

- `Document` 只在 `TYPE_CHECKING` 下 import。執行期的 `formats` <-> `workspace` 循環（D-5）維持原樣：loader 與 writer 仍在函式內 import `documents.workspace`。
- `context` 是每個 writer **必填**的第三個位置參數。漏給會丟出 `TypeError`，忘記遵守契約的 writer 會明確失敗。所有 writer 都回傳寫出的 `Path`：
  - `_write_dep(path, document, context)` 忽略 `context`，跟現在一樣回傳 `save_document_package(path, document, include_pending_metadata=False)`。
  - `_write_brl(path, document, context)` 忽略 `context`，跟現在一樣回傳 `export_document_brl(path, document)`。
  - `_write_html(path, document, context)` 忽略 `document`，把 `render_dual_view_html(build_dual_view_model(context.dual_view_results))` 以 UTF-8 寫到 `Path(path)`，並回傳該 `Path`。它**不會**開始建立上層目錄（那會改變行為）。唯一的差異是沒有人讀取的回傳值：從字元數改為 `Path`。
- Registry 值。只有新欄位與 `N_()` 包裝改變，其他值都不變：

  | key | `wildcard_label` | `export_wildcard` | `export_label` |
  | --- | --- | --- | --- |
  | dep | `N_("DEP")` | `N_("DotExpress files (*.dep)\|*.dep")` | `N_("Package DEP")` |
  | docx | `N_("DOCX")` | `None` | `None` |
  | epub | `N_("EPUB")` | `None` | `None` |
  | pdf | `N_("PDF")` | `None` | `None` |
  | txt | `N_("TXT")` | `None` | `None` |
  | brl | `N_("BRL")` | `N_("Braille files (*.brl)\|*.brl")` | `N_("Braille BRL")` |
  | html | `"HTML"`（不標記） | `"HTML files (*.html)\|*.html"`（不標記） | `N_("Dual View HTML")` |

  兩個 html 字串不標記，因為標記會新增兩個 msgid，那是在範圍外的在地化變更。html 項目上加一行註解說明。兩者目前都不是 msgid，所以 UI 以英文顯示，畫面與之前相同。
- `ALL_SUPPORTED_FILES_LABEL = N_("All Supported Files")` 是模組常數。`build_import_wildcard` 使用 `translate(ALL_SUPPORTED_FILES_LABEL)`，`get_import_filter_labels` 以它作為最後一個 label。匯入 wildcard 文字不變。
- 新增 `build_export_wildcard(descriptor, translate=lambda value: value) -> str`，與 `build_import_wildcard` 對稱，回傳 `translate(descriptor.export_wildcard)`。`descriptor.export_wildcard is None` 時丟出 `ValueError(f'Unsupported export format: "{descriptor.key}".')`。
- `get_exportable_formats()` 保留，現在有 production 呼叫者：`ui/action_menu.py` 與測試。
- Registry 不變式（有測試）：對每個 descriptor，`exportable`、`writer is not None`、`export_wildcard is not None`、`export_label is not None` 四者全為真或全為假。

### 孤立的 msgid（決策）

C 組四個字串沒有定義處，因為匯入對話框使用合併的 `build_import_wildcard`，而 P0-3 刪除了沒有用到的 `IMPORT_WILDCARDS`。**決策（orchestrator）：刪除它們。** 不保留任何替代的 tuple：保留無用字串違背 P0-3 的清理。357 這個數字只是「沒有任何顯示中的字串失去翻譯」的替代指標，而這四個字串從不顯示。

影響：

- 原始碼擷取出 353 個 msgid：357 個基線恰好減去 "Text files (*.txt)|*.txt", "PDF files (*.pdf)|*.pdf", "Word documents (*.docx)|*.docx", "EPUB books (*.epub)|*.epub"。掃描不得出現其他差異。
- `client/locales/dotexpress.pot`、`dotexpress.po` 與 `.mo` 不手動修改（與 P0-2、P0-5 相同）。在下次於 Windows 執行 `scripts\generate-pot.bat` 之前，它們仍保留這四個條目。之後 `.pot` 會移除它們，`msgmerge` 會把 `.po` 中的條目變成 obsolete（`#~`）條目。這無害，因為這些字串從不被查詢。此事列為 Windows 後續工作。

### 選單 descriptor（`ui/action_menu.py`）

```python
EnabledWhen = Literal["always", "has_selection", "has_documents"]

@dataclass(frozen=True)
class DocumentMenuItem:
    kind: str                      # "command" or "submenu"
    label: str                     # untranslated, N_()-marked
    action: str                    # unique key; handlers and state use it
    enabled_when: EnabledWhen
    formats: tuple[tuple[str, str], ...] = ()   # submenus: (format_key, untranslated label)

_EXPORT_FORMATS = tuple((d.key, d.export_label) for d in get_exportable_formats())
```

`DOCUMENT_MENU_ITEMS` 以 keyword 參數建立。順序、label 與 action 都不變：

| action | label | kind | enabled_when |
| --- | --- | --- | --- |
| open | `N_("Open")` | command | has_selection |
| delete | `N_("Delete")` | command | has_selection |
| delete_all | `N_("Delete All")` | command | has_documents |
| add | `N_("Add")` | command | always |
| rename | `N_("Rename")` | command | has_selection |
| import | `N_("Import")` | command | always |
| export | `N_("Export")` | submenu，`formats=_EXPORT_FORMATS` | has_selection |
| export_all | `N_("Export All")` | submenu，`formats=_EXPORT_FORMATS` | has_documents |

`_EXPORT_FORMATS` 的值為 `(("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`，與現在相同。Export 子選單的順序現在就是 registry 順序。

`get_document_menu_enabled_state(*, has_selection, has_documents) -> dict[str, bool]` 回傳 `{item.action: conditions[item.enabled_when] for item in DOCUMENT_MENU_ITEMS}`，其中 `conditions = {"always": True, "has_selection": has_selection, "has_documents": has_documents}`。dict 順序就是 descriptor 順序，所以 `Enable` 的呼叫順序與現在相同。`get_document_menu_descriptors()` 不變。

`ui/action_menu.py` 現在會 import `documents.formats`（為了 `get_exportable_formats`）與 `i18n`（為了 `N_`），兩者都是純模組。`ui/import_dialog.py` 已經以同樣方式依賴 `documents.formats`。

### 選單建構器（`ui/menu_builder.py`，新增，不 import wx）

```python
def build_document_menu(
    menu,
    handlers: Mapping[str, Callable[..., None]],
    *,
    translate: Callable[[str], str],
    new_menu: Callable[[], object],
    menu_event: object,
    item_id: int,
    descriptors: Sequence[DocumentMenuItem] | None = None,   # default get_document_menu_descriptors()
) -> dict[str, object]:
    ...

def apply_document_menu_state(items_by_action: Mapping[str, object], enabled_by_action: Mapping[str, bool]) -> None:
    ...
```

`build_document_menu` 以相同順序做出與目前 `gui` 完全相同的呼叫：

1. 若 `set(handlers)` 與 descriptor 的 action 集合不同，在碰 `menu` 之前就丟出 `ValueError`。訊息為 `Document menu handlers do not match the menu actions: missing [...], extra [...].`，`missing` 依 descriptor 順序，`extra` 排序過。缺少的 handler 或殘留的多餘 handler 會在建立時失敗；現在 label 打錯則會以 `KeyError` 失敗或被靜默略過。
2. **Append 階段**，依 descriptor 順序。command 變成 `menu.Append(item_id, translate(label))`。submenu 變成 `submenu = new_menu()`，接著 `menu.AppendSubMenu(submenu, translate(label))`，再依序對每個格式 `submenu.Append(item_id, translate(format_label))`。
3. **Bind 階段**，依 descriptor 順序，永遠綁在頂層 `menu` 上。command 變成 `menu.Bind(menu_event, handlers[action], item)`，handler 會收到 wx event。每個子選單格式項目變成 `menu.Bind(menu_event, lambda _event, key=format_key, handler=handlers[action]: handler(key), item)`，其中 `format_key` 跟現在一樣是 `format_key.casefold()`。descriptor 中所有 command 都在 submenu 之前，所以綁定順序與現在完全相同。
4. 回傳以 action 為 key 的頂層項目（command 項目與 `AppendSubMenu` 的回傳值）。

`apply_document_menu_state` 依 `enabled_by_action` 的順序，對每一項呼叫 `items_by_action[action].Enable(enabled)`。沒有對應項目的 action 會丟出 `KeyError`；現在則是靜默略過。在 production 中兩個 dict 都來自同一組 descriptor。

建構器完全不知道 wx。`gui` 在呼叫時傳入 `new_menu=wx.Menu`、`menu_event=wx.EVT_MENU`、`item_id=wx.ID_ANY`，測試則傳入記錄用的 fake。依 refactor.md 4.3 節與第 7 節第 4 點，不做 fluent API，也不做抽象 View。

一個使用者看不到的小差異：子選單 handler 是建立選單時取得的 bound method，而現在 `self.on_export_document` 是在事件觸發時才查找。command handler 現在本來就在 bind 時取得，production 也從不替換這些方法。File 選單只建立一次，右鍵選單每次彈出都重建。

### `gui.py`

- 刪除：`DEP_WILDCARD`、`BRL_WILDCARD`、`HTML_WILDCARD`、`_get_dep_wildcard`、`_get_brl_wildcard`、`_get_html_wildcard`、`_get_export_wildcard`、`_append_document_menu_items`、`_bind_document_menu_handlers`、`_MENU_TRANSLATION_MARKERS` 及其註解、`i18n` import 中的 `N_`，以及 `ui.action_menu` import 中的 `get_document_menu_descriptors`（步驟 5 之後只有 `ui/menu_builder.py` 讀取 descriptor；`tests/test_removed_dead_code.py` 只要求這個函式存在於 `ui.action_menu`，它仍然存在）。
- 新增 `_document_menu_handlers()`，回傳 `{"open": self.on_open_document, "delete": self.on_delete_document, "delete_all": self.on_delete_all_documents, "add": self.on_add_document, "rename": self.on_rename_document, "import": self.on_import_document, "export": self.on_export_document, "export_all": self.on_export_all_documents}`。
- 新增 `_append_document_menu(menu)`，回傳 `build_document_menu(menu, self._document_menu_handlers(), translate=_, new_menu=wx.Menu, menu_event=wx.EVT_MENU, item_id=wx.ID_ANY)`。
- `_create_document_menu()` 依序執行 `menu = wx.Menu()`、`items = self._append_document_menu(menu)`、`self._sync_document_menu_state(items)`，回傳 `menu, items`。`self._document_menu_items` 現在以 action 為 key。
- `on_document_context_menu` 以 `self._append_document_menu(menu)` 加上 `self._sync_document_menu_state(menu_items)` 建立彈出選單。hit-test、選取、彈出位置、`PopupMenu` 與 `Destroy` 都不變。
- `_sync_document_menu_state` 保留它的防禦與 `has_selection`/`has_documents` 計算，迴圈改為 `apply_document_menu_state(target_items, get_document_menu_enabled_state(...))`。
- `_export_document_with_dialog` 改用 `wildcard = build_export_wildcard(descriptor, _)`，其餘不變。
- `_write_export_document` 保留 `get_format(format_key)` 查找與不可匯出格式的 `ValueError`，然後對每種格式都呼叫 `descriptor.writer(destination_path, document, ExportContext(dual_view_results=self._dual_view_results_by_document.get(document.name, ())))`。這個方法中不再有任何格式 key 字面值。cache 仍在寫出時讀取，所以 Export All 與匯出前的轉換看到的 cache 與之前相同。
- `on_output_text_key_down` 保留 `get_format("brl").key`。那是 Ctrl+S 快速鍵選擇自己的格式，不是 writer 特例。
- `_create_menu_bar` 與 Translation、Help 選單不變，只有它們的 label 來源 `ui/translation_menu.py` 加上 `N_()`。

### 其他定義處

- `ui/translation_menu.py`：五個 label 都以 `N_()` 包起來（`from i18n import N_`）。清單的值不變。
- `dialog.py`：`CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")`，import 改為 `from i18n import N_, _`。`_(CSV_WILDCARD)` 的用法不變。
- `conversion/preprocessing/user_script.py`：兩個訊息改為 `raise ValueError(N_("..."))`（`from i18n import N_`）。例外文字不變，`settings/dialogs.py:148` 仍在顯示時翻譯。UI 以外的模組只 import `N_`，從不 import `_`，所以它們產生的值仍是未翻譯的。

### 遷移步驟（每步一個測試全綠的 commit；細節由 plan 決定）

1. `test:` 加入特性測試（見測試計畫），在未修改的程式上通過。
2. `refactor:` 單一 writer 契約。加入 `ExportContext` 與型別別名，writer 改為三個參數並回傳 `Path`，`gui._write_export_document` 統一呼叫，同時更新 `test_gui_document_flows` 中的兩個 writer 測試與 `test_document_formats` 的 HTML writer 測試。
3. `refactor:` 由 registry 推導匯出 wildcard 與 Export 子選單。加入 `export_wildcard`/`export_label`（以 `N_` 標記）、`build_export_wildcard` 與 `_EXPORT_FORMATS`。刪除 `gui` 的 wildcard 常數與方法，並在同一個 commit 中移除 `test_dead_frame_helpers_are_removed` 的兩個正向斷言。`gui` 的標記還在，所以 msgid 集合不變。
4. `refactor:` 文件選單狀態改以 action 為 key。加入 `enabled_when` 與以 action 為 key 的 `get_document_menu_enabled_state`，更新 `test_action_menu` 與 `test_sync_document_menu_state_before_document_list_exists`。`gui` 的綁定在同一個 commit 中改用 action key，所以沒有任何一步會混用 label 與 action key。
5. `refactor:` 加入 `ui/menu_builder.py` 與 `tests/test_menu_builder.py`，讓 File 選單與右鍵選單改走它。刪除 `_append_document_menu_items` 與 `_bind_document_menu_handlers`。
6. `refactor:` 在定義處標記可翻譯 label。在 `ui/action_menu.py`、`ui/translation_menu.py`、`documents/formats.py`（`wildcard_label`、`ALL_SUPPORTED_FILES_LABEL`）、`dialog.py`、`user_script.py` 加上 `N_()`。刪除 `_MENU_TRANSLATION_MARKERS` 與 `gui` import 中的 `N_`，並在同一個 commit 中更新 `SharedSetupConsumerTest`（`gui.py` 改為 `{"_", "resource_path"}`，`dialog.py` 改為 `{"N_", "_"}`），以及把 `test_gui_menu_translation_markers_use_n_` 替換成 `test_former_marker_strings_are_still_extracted`。

每一步完成後執行 msgid 掃描。步驟 1-5 之後為 357 個 msgid，與 `.pot` 以及 `p12/base_msgids.json` 相等。步驟 6 之後為 353 個，與兩者的差異只有 C 組那四個字串。

## 保持不變的部分

- File 選單、Export/Export All 子選單與右鍵選單：項目順序、巢狀結構、經 `_()` 翻譯的 label、ID（`wx.ID_ANY`）、綁定目標（頂層 menu）、綁定順序、每個項目呼叫哪個 frame 方法與帶哪個格式 key，以及在每種 `has_selection`/`has_documents` 組合下的 `Enable` 值與順序。
- 選單列：File、Translation、Help 的順序，項目與 handler 都相同。之前之後都沒有加速鍵或助記符。鍵盤快速鍵與 Ctrl+S 匯出 BRL 不變。
- 匯出對話框：標題、`defaultFile`、wildcard 文字（同樣三個字串的 `_()`）、style 旗標、副檔名修正，以及 `braille is None` 時的匯出前轉換。
- Export All：目錄對話框、衝突偵測、覆寫確認、逐份文件轉換、結果對話框與目標路徑。
- 匯出位元組：DEP zip 的成員與內容（`<name>.txt`、`<name>.brl`，沒有 pending-metadata 成員）、BRL 文字，以及 HTML 文字（對同一份 cache 結果做相同的 render；沒有 cache 時是帶英文預設訊息的「No conversion data」頁面）。
- 錯誤：不可匯出格式的 `ValueError('Unsupported export format: "<key>".')`，以及訊息相同的 `OSError` 處理。
- 匯入對話框的 wildcard 與 filter-index 對應。`formats.get_import_filter_labels` 與 `ui.import_dialog.*` 不變。
- msgid：每個會顯示的字串都保留它的 msgid 與翻譯。擷取集合是 357 個基線減去四個孤立匯入篩選字串（353 個）。`client/locales/` 不手動修改。下次於 Windows 執行 `generate-pot.bat` 時，`.pot` 的 `#:` 參照會位移（與 P0-5 相同），四個孤立字串也會離開 `.pot`。

刻意的差異，使用者都看不到：writer 回傳 `Path`（HTML writer 原本回傳 `int`）；匯出子選單 handler 在建立時取得；缺少或多餘的選單 handler，以及沒有對應選單項目的狀態項，現在會丟出例外而不是靜默略過；四個從不顯示的孤立匯入篩選字串不再被擷取。

## 測試計畫

先在現有程式上寫特性測試，讓預期值來自現在的行為。這些測試在步驟 2-6 中必須維持不變地通過，只有在它們呼叫的內部名稱改名時才能調整 setup。

### 特性測試（步驟 1，`tests/test_gui_document_flows.py`，新類別 `DocumentMenuAndExportCharacterizationTest`，11 個測試）

記錄用的 fake（`MenuRecorder`、`RecordedMenu`、`RecordedItem`、`fake_translate`）、逐字寫出的預期建立紀錄 `DOCUMENT_MENU_BUILD_LOG` 與 `enable_log(...)` helper 放在新的 helper 模組 `tests/menu_recording.py`（沒有 `test_` 前綴，所以 `discover` 不會收集它；不 import wx，所以不需要 stub scope），讓 `tests/test_menu_builder.py` 與同一份字面值比對。紀錄格式：`("new", "menu0")`、`("menu0", "Append", -1, "T[Open]")`、`("menu0", "AppendSubMenu", "menu1", "T[Export]")`、`("menu0", "Bind", "EVT_MENU", "menu1:T[Package DEP]")`、`("Enable", "menu0:T[Open]", False)`、`("menu0", "Destroy")`；項目命名為 `<所屬 menu>:<label>`。

這些測試使用記錄用的 `wx.Menu` fake：以 factory patch `gui.wx.Menu`，依建立順序把每個 menu 命名為 `menu0`、`menu1` 等，記錄 `Append(id, label)`、`AppendSubMenu(submenu, label)`、`Bind(event, handler, item)`，回傳的每個項目則記錄自己的 `Enable(value)` 呼叫。`gui.wx.EVT_MENU` patch 成 sentinel（`patch.object(..., create=True)`），因為在 stub 下，每次存取 wx 模組的屬性都會產生新的 class。`gui._` patch 成 `lambda s: f"T[{s}]"`，藉此證明每個 label 都經過翻譯。frame 的 handler 方法在建立選單**之前**就以 `Mock` 設在 instance 上。

1. **File 選單紀錄。** `frame._create_document_menu()` 的紀錄必須恰好是：建立 `menu0`；`Append(-1, "T[Open]")`、`T[Delete]`、`T[Delete All]`、`T[Add]`、`T[Rename]`、`T[Import]`；建立 `menu1`；`menu0.AppendSubMenu(menu1, "T[Export]")`；`menu1.Append(-1, …)` 依序為 `T[Package DEP]`、`T[Braille BRL]`、`T[Dual View HTML]`；`T[Export All]` 的 `menu2` 同理；接著 12 次 `menu0.Bind(EVT_MENU, …)`，順序為 Open、Delete、Delete All、Add、Rename、Import、export dep/brl/html、export_all dep/brl/html；最後是 `Enable` 呼叫。預期紀錄在測試中逐字寫出。
2. **Handler 分派。** 以假 event 呼叫每個記錄到的 handler，恰好呼叫一個 frame 方法：command 帶著 event 呼叫 `on_open_document(event)` 等；`export/<key>` 呼叫 `on_export_document(key)`；`export_all/<key>` 呼叫 `on_export_all_documents(key)`，key 為 `dep`、`brl`、`html`。
3. **啟用狀態。** 兩種情況，透過 label 為 `T[...]` 的項目上記錄到的 `Enable` 呼叫檢查（不透過 dict key）。沒有 `document_list` 也沒有文件時：Open/Delete/Delete All/Rename/Export/Export All 為 `False`，Add/Import 為 `True`，順序如上。`document_list` mock 有選取且 controller 有文件時：八個全為 `True`。把回傳的項目存成 `frame._document_menu_items` 之後，也涵蓋了不帶參數的 `_sync_document_menu_state()`。
4. **右鍵選單**（兩個測試：`test_context_menu_on_item_selects_it_and_pops_up_below_it` 與 `test_keyboard_context_menu_without_selection_clears_it`）。以 mock 提供 `document_list` 的 `ScreenToClient`、`HitTest -> (0, flags)`、`GetFirstSelected`、`GetItemRect`、`GetItemCount`，`frame.on_document_context_menu(event)` 在新的 menu 上記錄到相同的 append/bind 紀錄，依「有選取且有文件」啟用項目，選取並 focus 第 0 項，呼叫 `PopupMenu(menu, (rect.x, rect.y + rect.height))`，然後 `Destroy()`。第二種情況是從鍵盤開啟（`wx.DefaultPosition`）、沒有選取項目但有文件：清除選取，Delete All、Add、Import、Export All 為 `True`，其他四項為 `False`，並在 `wx.Point(0, 0)` 彈出。鍵盤情況會設定 `frame._document_menu_items = {}`，因為 `_clear_document_selection()` 不帶參數呼叫 `_sync_document_menu_state()`，而在 stub frame 上，不存在的屬性是一個為真的 no-op 函式（wx stub 遮蔽）。
5. **選單列。** 記錄 `gui.wx.MenuBar`，`frame.Bind` 為 `Mock`：選單依序加入 `T[File]`、`T[Translation]`、`T[Help]`；Translation 包含 `T[Convert]`、`T[Dual View]`、`T[Text Processing]`、`T[Dictionary Management...]`、`T[Settings]`，綁到五個 frame handler；Help 包含 `T[Coseeing Website]`（`wx.ID_ANY`）與 `T[About]`（`wx.ID_ABOUT`）。
6. **匯出對話框 wildcard。** 對 `dep`、`brl`、`html` 呼叫 `_export_document_with_dialog(Document("alpha", "t", "b"), key)`，使用會回傳取消的記錄用 `wx.FileDialog`：標題 `T[Export Document]`、`defaultFile` 為 `alpha.<ext>`、wildcard 為 `T[DotExpress files (*.dep)|*.dep]` / `T[Braille files (*.brl)|*.brl]` / `T[HTML files (*.html)|*.html]`、style 為 `FD_SAVE | FD_OVERWRITE_PROMPT`，且沒有寫出任何東西。
7. **副檔名修正。** `brl` 的對話框回傳 `/tmp/x/out.TXT` 時寫到 `/tmp/x/out.brl`；回傳 `/tmp/x/out.BRL` 時寫到 `/tmp/x/out.BRL`。此測試中 `_write_export_document` 是 `Mock`。
8. **匯出位元組，使用真正的 writer。** 在暫存目錄中使用真正的 registry writer 與 `_write_export_document`：`Document("alpha", "text", None)` 的 DEP 恰好有 zip 成員 `alpha.txt` = `text` 與 `alpha.brl` = `""`；`Document("alpha", "text", "⠁⠃")` 的 BRL 檔為 `⠁⠃`（UTF-8）；有 cache 結果（一小份 `DualViewSegment` 清單）的 `alpha` 的 HTML 逐位元組等於測試中直接計算的 `render_dual_view_html(build_dual_view_model(results))`；沒有 cache 的文件的 HTML 等於 `()` 的 render。另外：HTML writer 寫到不存在的目錄時丟出 `OSError`（不會建立上層目錄），而 BRL writer 仍會建立不存在的上層目錄。
9. **Export All 逐文件的 cache。** 以同步的 `wx.CallAfter`、真正的 writer、只有 `alpha` 的 cache 呼叫 `_export_next_document([alpha, beta], dir, "html", ExportBatchResult())`，寫出 `alpha.html`（alpha 的 render）與 `beta.html`（空的 render）。
10. **Ctrl+S。** `on_output_text_key_down` 在按鍵 83 且按住 Ctrl 時呼叫 `_export_document_with_dialog(open_document, "brl")`，然後呼叫 `output_txt.SetFocus()`。

### 更新的測試

- `tests/test_document_formats.py`：HTML writer 測試以第三個參數傳入 `ExportContext(dual_view_results=(...))`。新增測試：以非空 context 呼叫 DEP 與 BRL writer 時，寫出的檔案與 `ExportContext()` 相同；每個 writer 恰有三個位置參數（`inspect.signature`），只給兩個參數會丟出 `TypeError`；每個 writer 回傳目的地 `Path`；registry 不變式；`build_export_wildcard` 對 dep/brl/html 給出三個字串（並套用 `translate`），對 txt 丟出 `ValueError('Unsupported export format: "txt".')`；`ALL_SUPPORTED_FILES_LABEL == "All Supported Files"`，`get_import_filter_labels()` 以 `ALL_SUPPORTED_FILES_LABEL` 結尾且完整值仍為 `["DEP", "DOCX", "EPUB", "PDF", "TXT", "All Supported Files"]`；`ExportContext()` 預設沒有結果（`test_export_context_defaults_to_no_results`）。既有的匯入 wildcard 測試保持不變。
- `tests/test_action_menu.py`：四個啟用狀態測試改以 action 為 key，真值相同。新增測試：action 不重複；每個 `enabled_when` 都是三種規則之一；label 依序為 Open、Delete、Delete All、Add、Rename、Import、Export、Export All；子選單 `formats` 等於 `tuple((d.key, d.export_label) for d in get_exportable_formats())`，也等於字面值 `(("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`。既有的子選單測試保留。
- `tests/test_gui_document_flows.py`：`test_write_export_document_uses_registry_writer` 預期 `writer(Path("/tmp/custom.dep"), document, ExportContext())`。新增一個相鄰測試，確認 `alpha` 有 cache 時 DEP writer 同樣收到 `ExportContext(dual_view_results=cached)`（統一的呼叫）。HTML 測試預期 `writer(path, document, ExportContext(dual_view_results=cached_results))`。`test_sync_document_menu_state_before_document_list_exists` 改用 action key。刪除 `test_dead_frame_helpers_are_removed` 中 `assertTrue(hasattr(gui, "DEP_WILDCARD"))`/`_get_brl_wildcard` 這兩行：本任務刻意移除了這些名稱。不新增不存在性的守門測試（P0 審查 M-2），改由下方驗收標準的 grep 負責。
- `tests/test_i18n.py::SharedSetupConsumerTest`：`gui.py` 改為 `{"_", "resource_path"}`，`dialog.py` 改為 `{"N_", "_"}`。本任務刻意改變了這兩個模組 import 的名稱。把這個測試改成負向斷言（M-2）留給 orchestrator 的後續處理。
- `tests/test_i18n.py::ExtractionMarkerTest`：在步驟 6 的 commit 中，以 `test_former_marker_strings_are_still_extracted` 取代 `test_gui_menu_translation_markers_use_n_`。舊 tuple 中仍會顯示的 44 個字串（48 減去 C 組四個孤立字串），每一個都必須是 `client/` 中（排除 `tests/` 與 `.venv/`，即 `generate-pot.bat` 的檔案集合）某個 `_()`/`N_()` 呼叫的字面值第一個參數。它不在乎標記放在哪裡，所以不是位置守門，但若某個定義處失去 `N_()` 就會失敗。它的註解避免出現舊常數的名稱，讓驗收 grep 2 保持沒有輸出。

### 新增的測試

- `tests/test_menu_builder.py`（不用 wx、不用 stub scope，直接 import `ui.menu_builder`）：
  - 以記錄用 fake 與 `translate=lambda s: f"T[{s}]"` 建立預設 descriptor 的選單，紀錄等於特性測試 1 的預期紀錄（不含 `Enable` 部分；使用 `tests/menu_recording.py` 中同一份 `DOCUMENT_MENU_BUILD_LOG` 字面值）。
  - command handler 照原樣綁定並收到 event；子選單 handler 收到 casefold 後的格式 key；綁定目標永遠是頂層 menu。
  - 回傳值：每個 action 一個項目，子選單 action 對應 `AppendSubMenu` 的回傳值。
  - 缺少或多出 handler 時丟出 `ValueError`，且不做任何選單呼叫。
  - 自訂 `descriptors`（一個 command 加上一個格式 key 大小寫混合的 submenu）依序建立並綁定。
  - `apply_document_menu_state` 依給定順序啟用，未知的 action 丟出 `KeyError`。
  - `ui/menu_builder.py` 沒有 import `wx`（以 AST 檢查其 import）。
- `tests/test_action_menu.py` 的 `test_menu_labels_have_zh_tw_translations`：每個文件選單 label、每個 Export 子選單 label、每個 Translation 選單 label，在 `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` 中都有 `msgstr` 非空的條目（測試內附一個小的 msgid/msgstr 解析器，會略過註解與 obsolete `#~` 條目；目前 `.po` 中沒有 fuzzy 條目）。共檢查 16 個 label：8 個文件選單、3 個 Export 子選單與 5 個 Translation 選單 label。這延續了被刪除的標記 tuple 的目的：選單確實有翻譯。它檢查的是使用者看得到的翻譯，而不是 `N_()` 放在哪裡。

分別單獨執行 `tests.test_menu_builder`、`tests.test_gui_document_flows`、`tests.test_action_menu`、`tests.test_document_formats`，再以數個固定 seed 打亂順序一起執行（scratchpad 的 `shuffle_harness.py`，seed 1-5）。`ui/menu_builder` 是 `gui` 在 `StubScope.loading()` 內 import 的新純模組（P0 審查備註）。

## 驗收標準

1. `grep -n '"html"' client/gui.py` 沒有輸出。
2. `grep -rnE '_MENU_TRANSLATION_MARKERS|DEP_WILDCARD|BRL_WILDCARD|HTML_WILDCARD|_get_export_wildcard|_get_(dep|brl|html)_wildcard|_append_document_menu_items|_bind_document_menu_handlers' client --include='*.py'` 沒有輸出。
3. `grep -nE 'menu_items\["|"Delete All"|"Export All"' client/gui.py` 沒有輸出（沒有以 label 為 key 的查找）。
4. `grep -nE '\bN_\b' client/gui.py` 沒有輸出。`grep -nE '^(import wx|from wx)' client/ui/menu_builder.py` 沒有輸出。
5. msgid 掃描：`python -I <scratchpad>/p12/tools/msgid_scan.py client --compare <scratchpad>/p12/base_msgids.json` 回報 353 個原始碼 msgid。它列出的差異（相對於 `.pot` 與已儲存的基線）恰好只有 C 組四個字串（"Text files (*.txt)|*.txt", "PDF files (*.pdf)|*.pdf", "Word documents (*.docx)|*.docx", "EPUB books (*.epub)|*.epub"）。因為這些預期中的差異，工具會以 1 結束。出現任何其他差異即不符合此標準。
6. `git diff main --stat -- client/locales scripts` 為空。
7. 聚焦驗證通過：
   `cd client && python3 -m unittest tests.test_document_formats tests.test_action_menu tests.test_menu_builder tests.test_gui_document_flows tests.test_i18n tests.test_removed_dead_code tests.test_translation_menu tests.test_export_results tests.test_user_preprocessing_script tests.test_dictionary_management_dialog tests.test_wx_stub -v`（203 個測試，全部通過）。
8. 完整測試：`cd client && python3 -m unittest discover -s tests -p "test_*.py"` 回報 `failures=1`（只有已知的 P2-5 失敗）、`errors=0`、`skipped=7`，測試數為 614（575 加上 40 個新的測試執行，減去被替換的一個標記測試）。
9. 測試計畫中的打亂順序執行沒有新的失敗或錯誤。
10. Windows 上的項目（無法在這台 Linux 主機執行，列為驗證債，見下文）。

## 風險

- **使用者可見的選單，這裡沒有 wx**（中）。wxPython 沒有安裝，所以所有選單檢查都對記錄用 fake 執行。緩解：特性紀錄釘住每個 wx 呼叫（append、bind、enable 的順序、label、綁定目標），在變更前寫好，變更後不改。AGENTS.md 要求選單變更附截圖，這裡無法產生，列入 Windows 驗證債。
- **子選單綁定目標**（低）。wx 透過子選單項目目前所綁定的頂層 menu 傳遞事件。建構器以相同順序綁在同一個物件上，紀錄也斷言了綁定目標。
- **Handler 取得時機**（低）。Export 子選單 handler 改在建立選單時取得，而不是事件觸發時。production 從不替換 frame 方法，測試在建立前就設好 mock。
- **在 stub scope 內 import 新模組**（低）。`ui/menu_builder` 第一次是由 `gui` 在 stub scope 內 import。它不 import wx 也不 import gui，它的測試直接 import 它。打亂順序的執行涵蓋了模組順序。
- **領域模組 import i18n**（低）。`documents/formats.py`、`ui/action_menu.py`、`ui/translation_menu.py`、`conversion/preprocessing/user_script.py` 現在從 `i18n` import `N_`，import 時會載入一次 catalog。`i18n` 只 import 標準函式庫，所以沒有循環，也不會 import `config`（`test_translation_import_isolation` 仍成立）。這些模組從不呼叫 `_`。
- **嚴格性**（低）。不一致的 handler 對照表與未知的狀態 action 現在會丟出例外。所有呼叫端都由同一組 descriptor 建立兩者，測試也涵蓋了不一致的路徑。
- **Catalog 漂移**（低）。在新位置以 `N_` 標記會改變 `.pot` 的 `#:` 參照，會在 Windows 上刷新。刪除四個孤立字串後，它們會在那次執行時離開 `.pot`，`.po` 條目變成 obsolete。沒有地方顯示它們，所以使用者看到的翻譯不會遺失。掃描標準確保沒有其他 msgid 消失。
- **重疊**（低）。`_sync_document_menu_state` 中的 init 順序防禦屬於 P1-3，本任務保留。P1-4 會把 `_write_export_document`、`_export_next_document`、`_set_conversion_busy` 移到 `ExportCoordinator`/`ConversionPresenter`，`ExportContext` 讓它只需要一種乾淨的 writer 呼叫。D-5（`formats` <-> `workspace` 循環）不動。

## Windows 驗證債

- 變更前後，在出貨的 zh_TW UI 中截圖 File 選單、Export 與 Export All 子選單，以及文件清單的右鍵選單（在項目上開啟，以及在沒有選取項目時用鍵盤選單鍵開啟），並在「沒有文件」「有文件但沒有選取」「有選取」三種狀態下比對。
- 分別用變更前與變更後的 build 手動匯出每種格式（單一匯出與 Export All），比對輸出：DEP zip 的成員與內容、BRL 位元組、HTML 位元組。在輸出編輯區按 Ctrl+S 會開啟 BRL 存檔對話框。
- 執行 `scripts\generate-pot.bat`，確認重新產生的 `.pot` msgid 集合是基線恰好減去四個孤立匯入篩選字串（另外只有 `#:` 參照與建立日期改變）。接著對 zh_TW `.po` 執行 `msgmerge`（四個條目變成 obsolete `#~`），並重新編譯 `.mo`。

## 範圍外

- 把 `"HTML"` 或 `"HTML files (*.html)|*.html"` 加入 catalog、翻譯匯出 HTML 的「No conversion data」訊息，以及空白的 `"Close"` 翻譯。這些都是在地化變更。
- 用 `requires_braille` 讓 DEP/HTML 匯出略過轉換（行為變更）。
- `_set_conversion_busy` 的 `FindMenu(_("File"))` 查找（P1-4）、init 順序防禦（P1-3）以及 `ExportCoordinator`（P1-4）。
- 匯入對話框與 `ui/import_dialog.py` 的轉發 helper（refactor.md 5.1 節）。
- 字典管理對話框的按鈕（它們不是選單，P0-6 也已重構過該對話框）。
- 重新設計 `SharedSetupConsumerTest` 或合併 P0 守門測試（P0 審查 M-2 的後續）。
- 搬移 `Document` 或打破 `formats` <-> `workspace` 循環（D-5）。
