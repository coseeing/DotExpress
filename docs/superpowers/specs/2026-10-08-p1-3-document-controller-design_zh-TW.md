# DocumentController 全面採用（P1-3）設計

## 目標

把文件狀態與工作區檔案 IO 完整移出 `BrailleFrame`。本任務是 `storage/refactor.md`（6.2 節）路線圖的 P1-3，涵蓋 P-1（4.2 節「Controller 半採用」）、S-1（3.1 節）第 1 點「`DocumentWorkspaceService`」中關於文件 CRUD 與磁碟 IO 的部分，以及 S-6（3.1 節）中關於工作區 IO 協調的部分。

具體來說：

- **`DocumentController` 成為文件狀態的唯一擁有者（P-1）。** controller 補上 frame 缺少的方法（`add_document`、`add_documents`、`load_documents`、`select_document`、`document_name_at`、`has_documents`、`first_document_name`、`documents_snapshot`、`adjacent_document_name`、`document_name_exists`、`get_dual_view_results`、`set_dual_view_results`）。`BrailleFrame` 刪除四組轉發 property（`documents`、`_open_document_name`、`_selected_document_name`、`_dual_view_results_by_document`）、延遲建立的 `_get_document_controller()`，以及一行轉呼叫的包裝方法。frame 不再直接讀寫 controller 的清單、名稱或快取屬性。
- **單一、不依賴 wx 的工作區服務（S-1 第 1 點）。** 新增 `documents/workspace_service.py`，其中的 `DocumentWorkspaceService(controller, workspace_dir)` 依今日相同順序執行文件流程中每一個工作區磁碟操作，並同時做對應的 controller 更新：啟動載入、刪除無效檔案、儲存目前開啟的文件、新增、匯入時的寫入、重新命名（先寫新 package，再刪舊的）、刪除，以及 Delete All 與其失敗回滾（從磁碟重新載入並還原 controller）。frame 只保留對話框、確認、錯誤訊息、清單重新整理與編輯區更新。
- **初始化順序的防禦檢查消失。** controller 在 `BrailleFrame.__init__` 建立選單列之前就建立，因此 `_sync_document_menu_state` 不再需要 `hasattr(self, "documents")` 或 `hasattr(self, "_selected_document_name")`。

這是保持行為不變的重構。每個流程的磁碟效果與其順序、錯誤處理、對話框與訊息、選取與焦點結果，以及視窗標題都不變。沒有任何使用者可見字串改變，`client/locales/` 下不修改任何檔案。

起點（P0 階段審查第 5 點）：`prepare_document_for_save(document, *, text, braille) -> Document` 已是新簽名，`batch_export_documents_to_folder` 已刪除。服務建立在新簽名上，本任務不復活批次匯出。

## 現況（2026-10-08 於 `refactor/p1-3-document-controller` 驗證，HEAD `ef1988e`，已合併 P0-1..P0-6、P1-1 與 P1-2）

基準：`cd client && python -m unittest discover -s tests -p "test_*.py"` 執行 614 個測試，`failures=1`（已知的 P2-5 測試），`skipped=7`。路線圖的聚焦測試組 `tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows` 執行 120 個測試，OK。msgid 掃描回報 353 個原始碼 msgid，差異只有已知的四個「僅在 `.pot`」的匯入篩選孤立字串。

縮排：`gui.py` 與 `documents/session.py` 用 tab（`gui.py` 的 import 區塊有幾行 4 空白續行，維持原樣）。`documents/controller.py`、`documents/workspace.py` 與文件相關測試用 4 空白。新增的 `documents/workspace_service.py` 與 `tests/test_workspace_service.py` 用 4 空白。

### 轉發層（`gui.py`）

- `_get_document_controller()` 169-174 讀 `self.__dict__.get("_document_controller")`，沒有就延遲建立一個 controller。
- 176-206 中四組 property 把 `documents`、`_open_document_name`、`_selected_document_name`、`_dual_view_results_by_document` 轉發到 controller 的 `documents`、`open_name`、`selected_name`、`dual_view_results_by_document`。
- `_initialize_state` 222-229 設定 `self.workspace_dir = get_workspace_directory()`，建立**第二個** controller（`self._document_controller = DocumentController()`），再透過 property setter 指派 `[]`、`None`、`None`、`{}`。
- 為何需要延遲建立：`__init__` 在 `_initialize_state()` **之前**呼叫 `_initialize_frame()`（它建立選單列並呼叫 `_sync_document_menu_state(menu_items)`）。第一次同步時，property 會延遲建立一個沒有文件的拋棄式 controller，因此 File 選單以「無選取、無文件」的啟用狀態開始。`_sync_document_menu_state` 362-371 仍以 `hasattr(self, "documents")`、`hasattr(self, "_selected_document_name")`（因為 property 存在而恆為真）以及 `"document_list" in self.__dict__`（第一次同步時為假，因為清單控制項稍後才在 `_create_main_layout` 建立）作防禦。
- 一行包裝方法：`_get_document_names` 517、`_sort_documents` 558、`_get_document_by_name` 561、`_replace_document` 564、`_document_name_exists` 567（對 controller 的清單呼叫 `session.document_name_exists`）。
- 混合存取：部分流程直接呼叫 `self._document_controller.*`（重新命名 915、刪除 943、Delete All 975 與 984）；其他流程透過 property 直接改清單：`self.documents.append(document)` 761、`self.documents = documents` 822、`self.documents.extend(saved_documents)` 1015。dual-view 快取在 1379 以 `self._dual_view_results_by_document[self._open_document_name] = ...` 寫入，在 384 與 1130 讀取。
- `DocumentController.set_state(...)`（`documents/controller.py:52-63`）沒有呼叫者。

所有 `self.documents` 讀取點：369（`bool`）、581-590（清單重新整理）、700（相鄰文件）、801（第一份文件）、832-834 與 841-844（索引轉名稱）、856-859（右鍵選單命中）、945、955、978-979（是否為空與第一個名稱）、1036、1045、1048（Export All）。共 22 處。

### 各流程的磁碟效果、訊息與狀態

「先存檔」指 `_save_open_document_with_feedback()`；若它回傳 `False`，流程停止，之後什麼都不發生。`<ws>` 為工作區目錄，`<ws>/<name>.dep` 為 `document_package_path_for_name(name, <ws>)`。「錯誤框」指 `wx.MessageBox(template.format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)`（`_show_file_error`）。下列各處只捕捉 `OSError`；其他例外一律照今日往外拋。

| 流程 | 位置 | 磁碟效果（依序） | 失敗時 | 之後的狀態與 UI |
| --- | --- | --- | --- | --- |
| 啟動 | `_load_startup_documents` 299-303、`_load_workspace_documents_at_startup` 819-826 | 清空編輯區。`ensure_workspace_directory(<ws>)`（mkdir -p），再 `load_workspace_documents(<ws>)`（再次 mkdir -p、glob `*.dep`、逐一載入，載入失敗者收集為無效路徑；文件依 casefold 再依名稱排序）。 | mkdir 或 glob 的 `OSError` 不捕捉。 | 清單設為載入的文件。`_refresh_document_list()` 選取第一份。無效檔案審查（下一列）。`_ensure_open_document_exists()` 開啟第一份文件，或建立預設文件。更新標題，然後焦點移到原文編輯區。 |
| 無效檔案審查 | `_review_invalid_workspace_files` 733-745 | 只有在有無效路徑時：`InvalidWorkspaceFilesDialog(self, invalid_paths)`。使用者選擇刪除時，依序對每個路徑 `path.unlink(missing_ok=True)`。 | 每個路徑各自：錯誤框 "Failed to delete invalid workspace file: {error}"，然後**繼續**下一個路徑。 | 狀態不變。 |
| 儲存開啟中的文件 | `_save_open_document` 711-723、`_save_open_document_with_feedback` 725-731 | 沒有開啟中的名稱，或該名稱不在清單中：不做事。否則 `updated = prepare_document_for_save(document, text=input, braille=output)`（原本待轉換者 `braille` 保持 `None`）。**先替換記憶體中的文件**，再 `save_document_package(<ws>/<name>.dep, updated)`。 | 錯誤框 "Failed to save document: {error}"，回傳 `False`。記憶體保留新內容，因此在下一次成功存檔前，磁碟與記憶體不一致。 | 在開啟、新增、重新命名、刪除、Delete All（僅在有文件時）、匯入、匯出、Export All、Ctrl+S、Ctrl+Tab 切換與關閉視窗之前呼叫。關閉時若存檔失敗且 `evt.CanVeto()`，則否決關閉（`_on_close` 1258-1265）。 |
| 新增 | `on_add_document` 881-887、`_prompt_for_document_name` 768-789、`_create_document` 747-766 | 先存檔。以 `DocumentNameDialog(self, title=_("Add Document"), initial_name=...)` 詢問名稱並正規化。與既有名稱**完全相同（區分大小寫）**時顯示 `wx.MessageBox(_('Document "{name}" already exists.').format(name=...), _("Error"), wx.OK \| wx.ICON_ERROR, parent=self)`，並以該名稱預填重新詢問。取消：不做事。接著為 `Document(name, "", "")` 寫入 `<ws>/<name>.dep`（braille 為 `""`，因此沒有 pending metadata 成員）。 | 錯誤框 "Failed to save document: {error}"。狀態不變。 | 文件加到清單尾端。`_refresh_document_list(name)`，再 `_open_document_by_name(name)`（載入編輯區、游標移到 0、重新整理清單、標題、重新整理 dual view）。新增不移動焦點。 |
| 預設文件 | `_ensure_open_document_exists` 800-805、`_create_default_document` 791-798 | 只在清單為空時：`_create_document("new", "", None, focus_input=True)`，寫入**帶有** pending metadata 成員的 `<ws>/new.dep`。 | 同一個錯誤框。不建立文件，也沒有開啟中的文件。 | 與新增相同，之後焦點移到原文編輯區。 |
| 開啟 | `on_open_document` 872-879、`on_document_activated` 848 | 先存檔。 | — | `_open_document_by_name(selected)`，焦點移到原文編輯區。沒有選取：不做事（連存檔都不做）。 |
| Ctrl+Tab 切換 | `_open_adjacent_document` 698-709 | 目標 = `get_adjacent_document_name(documents, open 或 selected, step)`。沒有目標：不做事。否則先存檔。 | — | 開啟目標，焦點移到原文編輯區。 |
| 重新命名 | `on_rename_document` 889-920 | 選取的文件（清單選取，否則 controller 的選取名稱）；沒有：不做事。先存檔。再查一次文件；已不存在：不做事。以 "Rename Document" 詢問，預填目前名稱，重複檢查排除目前名稱。取消或同名：不做事。以文件的 text 與 braille 寫入 `<ws>/<new>.dep`（待轉換文件保持待轉換）。接著**若 `<ws>/<old>.dep` 存在**則刪除。 | 任一步驟的 `OSError`：錯誤框 "Failed to save document: {error}"。狀態不變。若是刪除失敗，兩個 package 都留在磁碟上。 | `controller.rename_document(old, new)`：清單項目、開啟與選取名稱、快取 key 都移到新名稱。`_refresh_document_list(new)`、標題、重新整理 dual view。不重新載入編輯區。 |
| 刪除 | `on_delete_document` 922-952 | 選取的文件；沒有：不做事。先存檔。確認 `wx.MessageBox(_('Do you want to delete document "{name}"?').format(...), _("Confirm Delete Document"), wx.YES_NO \| wx.NO_DEFAULT \| wx.ICON_WARNING, parent=self)`；不是 `wx.YES`：不做事。若 `<ws>/<name>.dep` 存在則刪除。 | 錯誤框 "Failed to delete document: {error}"。狀態不變。 | `controller.delete_document(name)`：移除項目與快取項目；偏好名稱為前一個鄰居，否則下一個；被刪的是開啟中文件時，開啟名稱移到偏好名稱；被刪的是選取文件時，選取名稱移到偏好名稱。`_refresh_document_list(selected)`。仍有文件且被刪的是開啟中文件：開啟偏好文件。沒有文件：更新標題、清空編輯區、建立預設文件。最後重新整理 dual view。 |
| Delete All | `on_delete_all_documents` 954-989 | 沒有文件：不做事（不存檔、不確認）。先存檔。確認 `_("Delete All will remove all documents. Do you want to continue?")`、`_("Confirm Delete All")`，旗標相同。接著依清單順序的**快照**逐一：若 `<ws>/<name>.dep` 存在則刪除。 | **第一個** `OSError` 發生時：**先**顯示錯誤框 "Failed to delete document: {error}"；再 `load_workspace_documents(<ws>)`（已刪除的 package 維持刪除）；`controller.restore_documents_after_delete_all_failure(remaining)`（替換清單、快取只保留磁碟上仍存在的名稱、開啟與選取名稱不在磁碟上時清除）；`_refresh_document_list()`；對重新載入得到的無效路徑做無效檔案審查；開啟第一份剩餘文件，或清空編輯區（此時**不**更新標題，也**不**建立預設文件）；重新整理 dual view；結束。重新載入本身的 `OSError` 會在錯誤框之後往外拋。 | 成功：`controller.delete_all_documents()`（清空清單、名稱與快取）；更新標題（顯示 "DotExpress"）；重新整理清單；清空編輯區；建立並開啟預設文件；重新整理 dual view。 |
| 匯入 | `on_import_document` 991-1024、`_persist_documents` 807-817 | 先存檔。`wx.FileDialog(self, _("Import Document"), wildcard=build_import_wildcard(_), style=wx.FD_OPEN \| wx.FD_MULTIPLE)`，篩選索引設為 All Supported；取消：不做事。超出範圍的篩選索引退回 All Supported。`batch_import_documents(paths, format_key=..., existing_names=set(names))`（以 casefold 檢查重複；載入失敗成為 `BatchIssue(path, str(exc))`）。接著依序為每份載入的文件寫入 `<ws>/<name>.dep`。 | 寫入失敗成為 `BatchIssue(path=<ws>/<name>.dep, reason=str(exc))`，迴圈繼續。未知格式 key 的 `ValueError` 不捕捉。 | 已儲存的文件依序加到清單尾端。恰好儲存一份：`_open_document_by_name(該文件)`（不移動焦點）。否則 `_refresh_document_list(open 或 selected)`。之後若「載入問題 + 儲存問題」（依此順序）不為空，顯示 `FileIssuesDialog(self, title=_("Import Issues"), message=_("Some files were skipped during import."), issues=["<檔名>: <原因>", ...])`。 |
| 選取變更 | `on_document_selection_changed` 839-846、`_get_selected_document_name` 828-834、`on_document_context_menu` 851-870 | — | — | 索引轉名稱。`wx.NOT_FOUND` 或超出尾端的索引得到 `None`（`_get_selected_document_name` 此時退回 controller 的選取名稱；`document_list` 尚未存在時直接回傳選取名稱）。右鍵選單命中項目時選取並聚焦該項目，並設為選取名稱；沒命中且沒有鍵盤選取時清除選取。 |
| 清單重新整理 | `_refresh_document_list` 578-595、`_clear_document_selection` 570-576 | — | — | 排序、重建清單控制項、偏好名稱存在則選取並聚焦它，否則第一項；設定選取名稱；同步選單狀態。清單為空時選取名稱設為 `None`。 |
| 手動轉換完成 | `_complete_conversion` 1335-1384 | **不寫磁碟。** | — | 有開啟中文件時，記憶體中的文件替換為（原文編輯區文字、轉換後點字），並 `cache[開啟名稱] = output.dual_view_segments`（即使開啟名稱不在清單中）。匯出時的轉換不動快取。 |
| 匯出、Export All、Ctrl+S | 1026-1048、1072-1080、`_write_export_document` 1126-1131 | 先存檔（匯出在存檔後重新讀取選取的文件）。Export All 走訪清單的複本。 | （P1-2，不變。） | 每份文件在寫入時才讀取快取。 |

### 目前涉及的測試

- `tests/test_document_controller.py`（11 個測試）與 `tests/test_document_session.py`（7 個）測試 controller 與 plan 函式。
- `tests/test_document_workspace.py`（20 個）測試 package、匯入、`prepare_document_for_save` 與 `load_workspace_documents`。
- `tests/test_gui_document_flows.py` 在 wx stub 下以 `object.__new__` 建立 frame。`GuiDocumentFlowsTest._make_frame` 透過轉發 property 設定狀態（`frame._dual_view_results_by_document = {}`、`frame._open_document_name = "alpha"`），並以對 `frame._documents_by_name` dict 操作的 lambda 取代 `_get_document_by_name` 與 `_replace_document`，而 `frame.documents` 一直是空清單。檔案中有 27 個敘述設定或讀取這些 property。`test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` patch `gui.document_package_path_for_name` 與 `gui.load_workspace_documents`；`test_save_open_document_saves_prepared_document` patch `gui.save_document_package`。這兩組 patch 點都會搬走。
- 沒有任何 GUI 測試涵蓋新增、重新命名、單筆刪除、Delete All 成功、匯入、啟動載入、無效檔案審查或預設文件。這些流程目前沒有安全網。
- wx stub 遮蔽（`tests/wx_stub.py`、`NoOpAttributes.__getattr__`）：在 stub frame 上，每個不存在的實例屬性都是 no-op 函式。因此沒有 `_document_controller` 的測試 frame 會拿到一個函式，而不是 `AttributeError`。測試必須一律明確設定 controller。

## 設計

### `DocumentController` 新增項目（`documents/controller.py`）

所有新方法都小而純。既有方法、屬性與其行為不變，只刪除沒有用到的 `set_state`。

| 方法 | 行為 |
| --- | --- |
| `add_document(document)` | 加到清單尾端。不排序（清單重新整理時會排序），不檢查重複（由名稱詢問負責，與今日相同）。 |
| `add_documents(documents)` | 依給定順序逐一加到尾端。 |
| `load_documents(documents)` | 以 `list(documents)` 替換清單，並清除開啟名稱、選取名稱與 dual-view 快取。啟動時這些本來就是空的，因此啟動結果不變。 |
| `select_document(name)` | 把選取名稱設為 `name`（可為 `None`）。與今日的指派相同，不做驗證。 |
| `document_name_at(index)` | `index` 位置的名稱；`index < 0`（涵蓋 `wx.NOT_FOUND == -1`）或 `index >= len` 時回傳 `None`。 |
| `has_documents`（property） | `bool(清單)`。 |
| `first_document_name`（property） | 第一份文件的名稱，或 `None`。 |
| `documents_snapshot()` | 含目前文件的新 `list`。修改它不影響 controller。 |
| `adjacent_document_name(step)` | `get_adjacent_document_name(清單, open_name or selected_name, step)`。 |
| `document_name_exists(name, exclude_name=None)` | `session.document_name_exists(清單, name, exclude_name=exclude_name)`（與今日相同，完全比對、區分大小寫）。 |
| `get_dual_view_results(name)` | `cache.get(name or "", ())`。 |
| `set_dual_view_results(name, results)` | `cache[name] = results`。 |

公開屬性（`documents`、`open_name`、`selected_name`、`dual_view_results_by_document`）保留，因為 controller 自己的測試使用它們。在 `documents/controller.py` 與其測試之外，沒有人讀寫它們；服務與 frame 只用方法。`open_document_name` 與 `selected_document_name` 仍是讀取用的 accessor。

### `DocumentWorkspaceService`（`documents/workspace_service.py`，新檔，不 import wx）

```python
@dataclass(frozen=True)
class ImportResult:
    saved: list[Document]       # 已儲存並加入，依 batch_import_documents 的順序
    issues: list[BatchIssue]    # 先載入問題，再儲存問題


@dataclass(frozen=True)
class DeleteAllResult:
    completed: bool             # 失敗並回滾後為 False
    invalid_paths: list[Path]   # 回滾重新載入時找到的無效 package，否則為 []


class DocumentWorkspaceService:
    def __init__(self, controller: DocumentController, workspace_dir: Path) -> None: ...
    @property
    def workspace_dir(self) -> Path: ...
    def package_path(self, name: str) -> Path: ...
    def load_documents(self) -> list[Path]: ...
    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None: ...
    def save_open_document(self, *, text: str, braille: str) -> Document | None: ...
    def create_document(self, document: Document) -> None: ...
    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult: ...
    def rename_document(self, source_name: str, new_name: str) -> Document | None: ...
    def delete_document(self, name: str) -> DeleteDocumentDecision: ...
    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult: ...
```

`workspace_dir` 為必填，沒有預設值。服務絕不呼叫 `get_workspace_directory(None)`。frame 傳入 `get_workspace_directory()`，因此 P2-6 之後可改傳 `ApplicationPaths.workspace`。服務重用 `documents/workspace.py`（`save_document_package`、`document_package_path_for_name`、`ensure_workspace_directory`、`load_workspace_documents`、`batch_import_documents`、`prepare_document_for_save`），不修改其中任何一個。

每個方法都依上表該流程所列，以相同順序執行：

- `load_documents()`：`ensure_workspace_directory(dir)`、`load_workspace_documents(dir)`、`controller.load_documents(documents)`，然後回傳無效路徑。`OSError` 往外拋。
- `delete_invalid_files(paths, on_error)`：對每個路徑 `path.unlink(missing_ok=True)`；遇到 `OSError` 呼叫 `on_error(exc)` 並繼續。
- `save_open_document(text, braille)`：沒有開啟中文件或它不在清單中時，不做任何 IO 並回傳 `None`。否則 `prepare_document_for_save`，再 `controller.replace_document(updated)`，再 `save_document_package(package_path(name), updated)`，回傳 `updated`。與今日相同，記憶體更新在寫入**之前**。`OSError` 往外拋。
- `create_document(document)`：`save_document_package(package_path(document.name), document)`，再 `controller.add_document(document)`。`OSError` 時不動 controller，錯誤往外拋。
- `import_files(paths, format_key)`：`batch_import_documents(paths, format_key=format_key, existing_names=set(controller.document_names))`，再逐一寫入載入的文件；寫入失敗成為 `BatchIssue(path=package_path(name), reason=str(exc))`。接著 `controller.add_documents(saved)`。回傳 `ImportResult(saved, load_issues + save_issues)`。未知格式 key 的 `ValueError` 照今日往外拋。
- `rename_document(source_name, new_name)`：兩個名稱相同時不做 IO，丟出 `ValueError`（frame 從不這樣呼叫；此防護避免方法刪掉剛寫入的 package）。來源不在清單中時不做 IO，回傳 `None`。否則以 `Document(new_name, source.text, source.braille)` 寫入 `package_path(new_name)`，再於 `package_path(source_name)` 存在時刪除它，然後回傳 `controller.rename_document(source_name, new_name)`。任一步驟的 `OSError` 往外拋，且不動 controller。
- `delete_document(name)`：`package_path(name)` 存在時刪除，再回傳 `controller.delete_document(name)`。`OSError` 時不動 controller，錯誤往外拋。與今日相同，frame 只對清單中的文件呼叫。
- `delete_all_documents(on_error)`：對 `controller.documents_snapshot()` 中的每份文件，若其 package 存在則刪除。第一個 `OSError` 發生時：**先**呼叫 `on_error(exc)`，再 `load_workspace_documents(dir)`，再 `controller.restore_documents_after_delete_all_failure(remaining)`，回傳 `DeleteAllResult(False, invalid_paths)`。若重新載入本身失敗，該錯誤在 `on_error` 執行後往外拋，與今日相同。成功：`controller.delete_all_documents()`，回傳 `DeleteAllResult(True, [])`。

為何 Delete All 用回呼、其他地方用例外：其他流程在失敗後唯一發生的事就是顯示錯誤框，因此 frame 可以直接捕捉 `OSError`。Delete All 的錯誤框則在重新載入**之前**，而重新載入本身也可能失敗；回呼可完全保留這個順序。這正是 refactor.md 4.3 節與 `dictionaries/name_prompt.py` 已採用的「純 presenter + callable」風格。

服務持有 controller 的參考。frame 只建立兩者各一次，之後不替換。需要不同 controller 的測試會用它另建一個服務（見下方測試 helper）。

### `BrailleFrame`（`gui.py`）

建構：

- `__init__` 在 `self.translation_runtime = runtime` 之後、`_initialize_frame()` 之前建立 `self._document_controller = DocumentController()`。因此第一次選單同步看到的是真正的空 controller，得到的「無選取、無文件」狀態與今日的拋棄式 controller 相同。
- `_initialize_state` 不再建立 controller，也不再指派四個狀態值。它把 `self.workspace_dir = get_workspace_directory()` 改為 `self._workspace_service = DocumentWorkspaceService(self._document_controller, get_workspace_directory())`。`get_workspace_directory` 仍 import 在 `gui` 中（測試在那裡 patch 它）。
- 移除 `workspace_dir` 屬性。它唯一的讀者是文件流程，現在都經由服務。

從 `gui.py` 刪除：`_get_document_controller`、四組 property、`_get_document_names`、`_sort_documents`、`_get_document_by_name`、`_replace_document`、`_document_name_exists`、`_persist_documents`，以及因此不再使用的 import（`document_name_exists`、`get_adjacent_document_name`、`document_package_path_for_name`、`ensure_workspace_directory`、`load_workspace_documents`、`prepare_document_for_save`、`save_document_package`、`batch_import_documents`；`BatchIssue`、`Document`、`DEFAULT_DOCUMENT_NAME`、`create_default_document`、`normalize_document_name` 保留，因為 frame 仍會用到）。

保留，名稱與呼叫者不變：`_save_open_document`、`_save_open_document_with_feedback`、`_create_document`、`_create_default_document`、`_ensure_open_document_exists`、`_prompt_for_document_name`、`_review_invalid_workspace_files`、`_load_workspace_documents_at_startup`、`_refresh_document_list`、`_clear_document_selection`、`_open_document_by_name`、`_open_adjacent_document`、`_get_selected_document_name`、`_get_selected_document`、`_sync_document_menu_state`、`_update_window_title`、`_render_dual_view_for_open_document`、`_write_export_document`、`_complete_conversion`，以及所有 `on_*` handler。保留這些名稱，讓特性測試與 P1-2 的測試可以不經修改地對新程式碼執行。

保留的方法各自如何改變（只改內容）：

- `_sync_document_menu_state`：防禦改為 `if not target_items: return`。保留 `"document_list" in self.__dict__` 檢查（第一次同步時清單控制項仍不存在）。`has_documents=self._document_controller.has_documents`。
- `_update_window_title`、`_render_dual_view_for_open_document`、`_write_export_document`、`on_output_text_key_down`、`_complete_conversion`：讀取改用 `open_document_name`、`get_document`、`get_dual_view_results`；`_complete_conversion` 以 `replace_document` 與 `set_dual_view_results` 寫入。
- `_clear_document_selection`、`_refresh_document_list`、`on_document_selection_changed`、`on_document_context_menu`、`_get_selected_document_name`：改用 `select_document`、`sort_documents`、`document_names`、`selected_document_name` 與 `document_name_at`。`_refresh_document_list` 從 `document_names` 插入項目並選取 `names.index(selected)`；因為名稱唯一，這與今日迴圈找到的第一個符合項相同。
- `_open_adjacent_document`：`adjacent_document_name(step)`。`_ensure_open_document_exists`：`first_document_name`。`_prompt_for_document_name`：`document_name_exists`。
- `_save_open_document`：`self._workspace_service.save_open_document(text=self.input_txt.GetValue(), braille=self.output_txt.GetValue())`。
- `_create_document`：建立 `Document`，在既有的 `try/except OSError`（同一個錯誤框）中呼叫 `create_document`，之後照今日重新整理、開啟並聚焦。
- `_load_workspace_documents_at_startup`：`invalid_paths = self._workspace_service.load_documents()`，之後呼叫相同的重新整理、審查、確保開啟與標題。
- `_review_invalid_workspace_files`：對話框部分不變；刪除改為 `delete_invalid_files(invalid_paths, on_error=lambda exc: self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc))`。
- `on_import_document`：對話框部分不變；接著 `result = self._workspace_service.import_files(source_paths, format_key=format_key)`，依 `len(result.saved) == 1` 走相同的「開啟或重新整理」分支，並 `_show_file_issues_dialog(..., result.issues)`。
- `on_rename_document`：詢問部分不變；接著 `try: renamed = self._workspace_service.rename_document(selected_document.name, new_name)`，`except OSError` 時顯示同一個錯誤框（"Failed to save document: {error}"）；`None` 時返回；之後相同的重新整理、標題與 dual view 呼叫。
- `on_delete_document`：確認不變；接著 `try: decision = self._workspace_service.delete_document(name)`，錯誤框相同（"Failed to delete document: {error}"）；其餘改讀 `has_documents`、`selected_document_name` 與 `open_document_name`。
- `on_delete_all_documents`：以 `has_documents` 判斷是否為空；確認不變；`result = self._workspace_service.delete_all_documents(on_error=lambda exc: self._show_file_error(_("Failed to delete document: {error}"), exc))`。若 `not result.completed`：`_refresh_document_list()`、`_review_invalid_workspace_files(result.invalid_paths)`、開啟 `first_document_name` 或清空編輯區、重新整理 dual view、返回。否則執行與今日相同的成功收尾。
- `on_export_all_documents`：`has_documents` 與 `documents_snapshot()`（衝突掃描與批次共用同一份快照，今日兩者也是同一份清單）。

`_("...")` 字面值留在 `gui.py` 的相同呼叫處，因此 msgid 集合與 `.pot` 參照都不變。

### 遷移步驟（每一步是一個全綠的 commit；細節由 plan 說明）

1. `test:` 在 `tests/test_gui_document_flows.py` 加入特性測試（測試計畫 A 部分），在今日的程式碼上通過。
2. `refactor:` 加入 controller 方法並刪除 `set_state`，測試放在 `tests/test_document_controller.py`。`gui` 尚未使用。
3. `refactor:` 以測試先行加入 `documents/workspace_service.py` 與 `tests/test_workspace_service.py`（B 部分）。`gui` 尚未使用。
4. `refactor:` frame 改用 controller 方法。在 `__init__` 建立 controller；刪除轉發 property、`_get_document_controller` 與一行包裝方法；拿掉兩個 `hasattr` 防禦；替換上面列出的每一個狀態讀寫（包括 `_complete_conversion` 與匯出的讀取）。磁碟 IO 仍在 `gui` 中執行，目錄讀自 `self.workspace_dir`。同一個 commit 更新既有 GUI 測試的 setup（C 部分），因為它們指派的 property 已不存在。
5. `refactor:` 啟動、無效檔案審查、儲存開啟中文件、新增與預設文件建立改經由服務。`_initialize_state` 建立服務並移除 `workspace_dir`；重新命名、刪除、Delete All 與匯入中剩下的直接 IO 在第 6-7 步之前改讀 `self._workspace_service.workspace_dir`。
6. `refactor:` 匯入改經由服務；刪除 `_persist_documents`。
7. `refactor:` 重新命名、刪除與 Delete All 改經由服務，刪除 `gui` 中不再使用的工作區 import，並改寫兩個 patch `gui.document_package_path_for_name`、`gui.load_workspace_documents` 或 `gui.save_document_package` 的測試（C 部分）。

第 1 步的特性測試在之後每一步都必須不經修改地通過；只有它們共用的 setup helper 可以改（第 5 步在其中加入服務）。

## 保持不變的部分

- 上表每個流程的：先存檔呼叫與其中止、確認對話框（文字、標題、旗標）、磁碟操作與其順序、在何處捕捉哪種例外、錯誤框範本與標題，以及清單、開啟與選取名稱、快取、編輯區、焦點與標題的結果。
- package 內容：成員與 pending metadata 由未修改的 `save_document_package` 寫入。新增不寫 pending 成員；預設文件與待轉換文件會寫。
- 名稱詢問的完全比對（區分大小寫）重複檢查，以及匯入的 casefold 重複檢查。
- 啟動順序：清單、無效檔案審查、預設文件、標題、焦點。
- 選單狀態，包括文件清單存在前的第一次同步（P1-2 對 `_create_document_menu` 的特性紀錄不變）。
- msgid：沒有字串新增、移除或搬到其他模組。不動 `client/locales/` 與 `scripts/`。

刻意的差異（使用者看不到）：controller 改為在 `__init__` 建立一次，而不是延遲建立再於 `_initialize_state` 建立第二次；`load_documents` 另外清除開啟與選取名稱及快取，而它們在啟動時本來就是空的；刪除 `DocumentController.set_state`；服務的 `rename_document` 對相同名稱丟出 `ValueError`（GUI 無法觸及）。

## 測試計畫

### A. 特性測試（第 1 步，`tests/test_gui_document_flows.py`，新類別 `DocumentWorkspaceFlowsCharacterizationTest`）

先寫，對今日的程式碼執行，預期值取自今日行為。每個測試使用真實的暫存工作區目錄與真實的 `DocumentController`。類別 helper `_make_workspace_frame(workspace, documents, open_name=None, selected_name=None)` 以 `object.__new__` 建立 frame，設定 `frame._document_controller = DocumentController(...)` 與 `frame.workspace_dir = workspace`，並為 `input_txt`、`output_txt`、`document_list`（`GetFirstSelected` 回傳選取名稱的索引，或 `wx.NOT_FOUND`）與 `SetTitle` 設定 `Mock`，外加 `_dual_view_frame = None`、`_document_menu_items = {}` 以及 `_make_frame` 已設定的轉換相關屬性。第 5 步時 helper 另外設定 `frame._workspace_service = DocumentWorkspaceService(frame._document_controller, workspace)`，這是這些測試唯一的變動。斷言透過 `frame._document_controller` 的屬性讀取狀態（前後都存在），並以 `load_document_package` 與目錄列表讀取磁碟。

對話框在 `gui` 上 patch：`wx.MessageBox`（記錄呼叫，回傳 `wx.YES` 或 `wx.NO`）、`DocumentNameDialog`（依序回傳排定名稱或取消的 fake）、`wx.FileDialog`（回傳路徑與篩選索引）、`InvalidWorkspaceFilesDialog`（記錄路徑，回傳刪除選擇）、`FileIssuesDialog`（記錄標題、訊息與問題行）。

故障透過檔案系統注入，而非 patch 模組函式，因此不論 IO 由 `gui` 或服務執行，同一個測試都適用：在 `<ws>/<name>.dep` 放一個**目錄**，會讓 package 寫入失敗（`zipfile` 無法以寫入模式開啟目錄），也會讓 `unlink()` 失敗（Linux 上是 `IsADirectoryError`，Windows 與 macOS 上是 `PermissionError`，兩者皆為 `OSError`）。載入步驟會把這種目錄視為無效 package。錯誤框以標題（`_("Error")`）、旗標、parent，以及「以範本文字開頭並包含真實錯誤 `str(exc)`」的訊息檢查。

案例：

1. 新增：先儲存開啟中文件；詢問結果 `beta` 寫入 `beta.dep`，braille 為 `""` 且沒有 pending 成員；名稱為 `[alpha, beta]`；`beta` 為開啟且選取；編輯區已載入；標題 `beta - DotExpress`。
2. 新增，先重複再有效：第一個名稱 `alpha` 顯示 `Document "alpha" already exists.` 並以 `initial_name="alpha"` 重新詢問；第二個名稱被建立。
3. 新增，寫入失敗（`beta.dep` 是目錄）：一個錯誤框 "Failed to save document: ..."；controller 不變；`alpha` 仍開啟。
4. 預設文件：controller 為空時，`_ensure_open_document_exists()` 寫入帶 pending 成員的 `new.dep` 並開啟 `new`；焦點移到原文編輯區。
5. 啟動，空工作區：`_load_workspace_documents_at_startup()` 建立目錄與 `new` 文件。
6. 啟動，有無效 package：一個損毀的 `bad.dep` 與一個有效的 `good.dep`；審查對話框收到 `[bad.dep]`；選擇刪除後它被移除；`good` 被開啟。
7. 啟動，刪除無效檔案出錯：兩個無效項目，第一個無法刪除（非空目錄）；錯誤框 "Failed to delete invalid workspace file: ..." 出現一次，第二個仍被刪除。
8. 儲存開啟中文件：記憶體與 `alpha.dep` 都是編輯區文字；待轉換文件保持待轉換（有 pending 成員）。
9. 儲存開啟中文件，寫入失敗：`_save_open_document_with_feedback()` 回傳 `False` 並顯示 "Failed to save document: ..."；記憶體已是新文字（釘住「先記憶體」的順序）。
10. 存檔失敗時關閉：`_on_close` 否決事件。
11. 重新命名成功：`alpha.dep` 消失，`gamma.dep` 為 alpha 的內容（保留待轉換狀態）；名稱、開啟與選取名稱及快取 key 都移到 `gamma`；標題 `gamma - DotExpress`。
12. 舊 package 不存在時重新命名：寫入 `gamma.dep`，沒有錯誤。
13. 重新命名，寫入失敗（`gamma.dep` 是目錄）："Failed to save document: ..."；`alpha.dep` 完好；controller 不變。
14. 重新命名，刪除失敗（被選取但未開啟的文件，其 package 是目錄）："Failed to save document: ..."；新 package 存在且舊項目仍在；controller 不變。
15. 取消重新命名，以及重新命名為相同名稱：除先存檔的寫入外沒有磁碟變化；controller 不變。
16. 刪除開啟中的中間文件：檔案消失；開啟前一個鄰居；保留它的快取項目，刪除被刪文件的項目。
17. 刪除被選取但未開啟的文件：開啟中文件與編輯區不變。
18. 刪除最後一份文件：建立並開啟 `new`。
19. 刪除時回答 No：沒有任何變化。
20. 刪除，刪除檔案失敗："Failed to delete document: ..."；狀態不變。
21. Delete All 成功：所有 package 消失；建立並開啟 `new`；快取為空。
22. Delete All 失敗：`alpha.dep` 為檔案、`beta.dep` 為目錄、`gamma.dep` 為檔案。`alpha.dep` 被刪除、錯誤框出現在審查對話框之前（以共用 `Mock` parent 的單一有序呼叫紀錄檢查）、審查對話框收到 `[beta.dep]`、controller 為 `[gamma]`、快取只剩 `gamma`、開啟 `gamma`。
23. Delete All 失敗且沒有剩下有效文件：清空編輯區、不建立 `new`、失敗後不呼叫 `SetTitle`（釘住今日行為）。
24. 沒有文件時 Delete All：不存檔、不確認。
25. 匯入兩個 `.txt`：兩個 package 都寫入；名稱已加入；開啟中文件維持開啟；沒有問題對話框。
26. 匯入一個檔案：它被開啟。
27. 匯入時有重複且有寫入失敗：問題對話框顯示 `Import Issues` / `Some files were skipped during import.`，載入問題行在儲存問題行（`<name>.dep: <原因>`）之前；只有已儲存的文件被加入。
28. 選取變更：索引 1 選取第二個名稱；`wx.NOT_FOUND` 與超出尾端的索引選取 `None`。

既有的 `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` 在第 1 步保留，於第 7 步改寫（C 部分）。

### B. `tests/test_workspace_service.py`（新檔，第 3 步，不用 wx 也不用 stub scope）

測試先行，使用暫存目錄與真實的 `DocumentController`：

- `load_documents`：建立目錄、把排序好的文件載入 controller、回傳無效路徑、清除開啟與選取名稱。
- `delete_invalid_files`：刪除每個路徑，對失敗路徑呼叫一次 `on_error`，然後繼續。
- `save_open_document`：記憶體與磁碟都更新；待轉換 braille 保持待轉換；沒有開啟中文件時回傳 `None` 且不產生檔案；寫入失敗時錯誤在 controller 更新**之後**往外拋。
- `create_document`：先寫 package 再加入；失敗時什麼都不加入，錯誤往外拋。
- `import_files`：已儲存的文件依序加入；寫入失敗成為帶 package 路徑與 `str(exc)` 的 `BatchIssue`；載入問題在儲存問題之前；未知格式 key 丟出 `ValueError`。
- `rename_document`：新 package 為來源內容，且**舊 package 被刪除**；舊 package 不存在也沒問題；寫入失敗與刪除失敗各自往外拋且 controller 不變（刪除失敗時兩個 package 都在磁碟上）；未知來源回傳 `None` 且不做 IO；相同名稱丟出 `ValueError` 且 package 留在原地。
- `delete_document`：刪除 package，回傳並套用決策；package 不存在也沒問題；刪除失敗時往外拋且 controller 不變。
- `delete_all_documents`：成功時清空磁碟、清單、名稱與快取，回傳 `completed=True`；**失敗時**失敗項目之前的 package 已刪除、`on_error` 恰好呼叫一次且在重新載入之前（在回呼內記錄目錄列表來檢查）、之後 controller 與磁碟一致、快取只保留磁碟上仍存在的名稱、開啟與選取名稱已不存在時被清除、回傳無效路徑、剩下的文件不被動到。
- 模組不 import `wx` 也不 import `gui`（以 AST 檢查其 import）。

### C. 更新的測試

- `tests/test_document_controller.py`：為每個新方法加測試（包括 `document_name_at(-1)`、超出尾端的索引、快照是複本、`load_documents` 清除名稱與快取、`adjacent_document_name` 先用開啟名稱再用選取名稱）。
- `tests/test_gui_document_flows.py`：
  - `GuiDocumentFlowsTest._make_frame(documents=(Document("alpha", "source", None),), open_name="alpha")` 建立 `frame._document_controller = DocumentController(...)`，並從第 5 步起建立一個指向佔位目錄的服務。刪除 `_documents_by_name` dict 與 `_get_document_by_name`/`_replace_document` lambda；測試改經 controller 讀取文件。
  - 需要空工作區的測試傳入 `documents=()`：`test_sync_document_menu_state_before_document_list_exists`，以及 `DocumentMenuAndExportCharacterizationTest._make_menu_frame`（其預期紀錄假設在 `_select_first_of` 之前沒有文件）。`_select_first_of` 以 `frame._document_controller.load_documents(...)` 載入名稱。
  - 所有 `frame.documents = ...`、`frame._open_document_name = ...`、`frame._selected_document_name = ...` 與 `frame._dual_view_results_by_document[...]` 改為 controller 建構參數或 controller 方法呼叫（`select_document`、`set_dual_view_results`），所有讀取改為 `open_document_name`、`selected_document_name` 或 `get_dual_view_results`。測試內容與預期值不變。
  - `_initialize_state_with_loaded_tables` 與 `test_initialize_state_wires_presenter_to_active_dictionary` 在呼叫 `_initialize_state` 之前設定 `frame._document_controller = DocumentController()`（否則 stub 遮蔽會把一個函式交給服務）。
  - `test_save_open_document_saves_prepared_document` 改為相同預期的暫存目錄測試（package 內容為 `Document("alpha", "edited", "edited braille")`）。
  - `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` 保留情境與斷言，但改以檔案系統（或 stub 服務）注入失敗，而不是 patch 已不在 `gui` 中的函式。
- 不新增「名稱不存在」守門測試（P0 審查 M-2），由驗收 grep 負責。不擴充 `test_dead_frame_helpers_are_removed`。

先單獨執行動到的模組，再以多個固定種子的隨機順序一起執行（scratchpad 的 `shuffle_harness.py`，種子 1-5）。`documents.workspace_service` 是 `gui` 在 `StubScope.loading()` 內首次 import 的新純模組，因此模組順序有影響（P0 審查註記與 I-1）。

## 驗收條件

1. `grep -nE '@property|\.setter|_get_document_controller' client/gui.py` 沒有輸出。
2. `grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' client/gui.py` 沒有輸出（沒有直接存取狀態，沒有 `self.documents` 清單操作）。
3. `grep -nE 'save_document_package|load_workspace_documents|ensure_workspace_directory|document_package_path_for_name|batch_import_documents|prepare_document_for_save|\.unlink\(' client/gui.py` 沒有輸出（所有工作區 IO 都在服務中）。
4. `grep -nE '_sort_documents|_get_document_by_name|_replace_document|_document_name_exists|_get_document_names|_persist_documents|\bworkspace_dir\b' client/gui.py` 沒有輸出。
5. `grep -nE 'hasattr\(self, "(documents|_selected_document_name)"\)' client/gui.py` 沒有輸出。
6. `grep -nE '^(import wx|from wx)|^from gui|^import gui' client/documents/workspace_service.py client/documents/controller.py` 沒有輸出。`grep -n 'set_state' client/documents/controller.py` 沒有輸出。
7. `grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' client/documents/workspace_service.py` 沒有輸出（服務只用 controller 方法）。這也是 `ImportResult` 的欄位命名為 `saved` 而不是 `documents` 的原因。
8. `git diff main --stat -- client/locales scripts` 為空，且 msgid 掃描輸出與本任務之前相同（353 個原始碼 msgid，只有已知的四個「僅在 `.pot`」孤立字串）。
9. 路線圖驗證通過：`cd client && python3 -m unittest tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v`。另加 `tests.test_removed_dead_code tests.test_menu_builder tests.test_action_menu tests.test_wx_stub`。
10. 完整測試：`cd client && python3 -m unittest discover -s tests -p "test_*.py"` 回報 `failures=1`（只有已知的 P2-5 失敗）、`errors=0`、`skipped=7`，測試數為 614 加上新測試（確切數字由 plan 決定）。
11. 隨機順序執行沒有新的失敗或錯誤。
12. Windows：見下方驗證債（在這台 Linux 主機上無法執行）。

## 風險

- **初始化順序**（中）。拿掉延遲建立後，若 controller 太晚建立，第一次選單同步會壞掉。緩解：在 `__init__` 中、`_initialize_frame()` 之前建立。P1-2 對 `_create_document_menu` 的特性紀錄（含 `Enable` 呼叫）不變，涵蓋此點。
- **測試中的 stub 遮蔽**（中）。在 stub frame 上，不存在的 `_document_controller` 或 `_workspace_service` 是 no-op 函式。緩解：每個 frame helper 都明確設定兩者，而特性測試斷言檢查真實的磁碟與 controller 狀態，因此缺少物件會明確失敗而不是靜默通過。
- **副作用順序**（中）。三個流程依賴順序：存檔（先記憶體再磁碟）、重新命名（先寫再刪）、Delete All（先錯誤框再重新載入）。特性測試 9、13、14、22 與服務測試各自釘住。Delete All 的回呼即使在重新載入本身失敗時也保持順序。
- **controller 身分**（低）。服務持有 controller。若測試或之後的程式碼替換了 `frame._document_controller`，服務會更新過期的物件。緩解：production 只建立一次；測試 helper 同時建立兩者；plan 中沒有任何重新指派 controller 的路徑。
- **patch 點變動**（低）。兩個 GUI 測試 patch 了 import 進 `gui` 的函式。它們改為使用檔案系統，因此不依賴 IO 位於何處。
- **在 stub scope 內 import 新模組**（低）。`documents.workspace_service` 只 import `documents.*` 與標準函式庫，它自己的測試直接 import 它。隨機順序執行涵蓋模組順序。
- **與 P1-4 重疊**（低）。P1-4 會把 `_write_export_document`、`_export_next_document` 與 `_complete_conversion` 搬到 `ExportCoordinator` 與 `ConversionPresenter`。本任務之後，它們只透過 `get_dual_view_results` 與 `set_dual_view_results` 讀寫快取，P1-4 可以直接注入。
- **僅 Windows 的檔案行為**（中，此處無法驗證）。在 Windows 上，其他程式開著檔案時 `unlink` 會失敗，這是 Delete All 回滾在實際使用中的觸發條件。測試以目錄讓 `unlink` 失敗，這在 Windows 上同樣會失敗（`PermissionError`），但檔案被鎖定的情況只能手動檢查。

## 調查中發現的既有缺陷（本任務不修）

這些缺陷今日就存在於 `main`。本任務保持行為不變，列出它們以便後續任務決定如何修正。

1. **在不區分大小寫的檔案系統（Windows、macOS 預設）上，只改大小寫的重新命名會刪掉文件。** 把 `Alpha` 改名為 `alpha` 會通過重複檢查（排除目前名稱且區分大小寫），寫入 `alpha.dep`（在 Windows 上與 `Alpha.dep` 是同一個檔案），接著 `Alpha.dep`「存在」而被刪除。package 消失，下次啟動時文件不見。
2. **在 Windows 上新增只差大小寫的名稱會覆寫另一份文件的 package。** 名稱詢問的重複檢查區分大小寫，因此在已有 `alpha` 時會接受 `Alpha`。寫入會取代 `alpha.dep`，其成員名稱為 `Alpha.*`，下次啟動時該檔案無法通過名稱檢查，被回報為無效。匯入沒有這個問題，因為它比較 casefold 後的名稱。
3. **重新命名時刪除舊檔失敗會讓兩個 package 都留在磁碟上**，而記憶體中的清單只保留舊名稱。下次啟動會顯示兩份文件。
4. **Delete All 回滾後沒有剩下任何有效文件時**，會清空編輯區，但不更新標題，也不建立預設文件。

修正 1 與 2 的做法是在名稱詢問中以 `casefold()` 比較（並在新舊路徑為同一檔案時跳過刪除）。這是使用者可見的行為變更，應另開任務處理。

## Windows 驗證債

- 在打包版本上，改動前後各走一次新增、重新命名、刪除、Delete All、匯入（單一與多個檔案，含重複）、Ctrl+Tab 與關閉視窗，比較工作區資料夾內容以及清單、標題與編輯區狀態。
- 讓其他程式（例如壓縮工具）開著一個 `.dep` 再執行 Delete All 以觸發回滾：先出現錯誤框，之後若有無效檔案則出現無效檔案對話框，最後是重新載入的清單。
- 在工作區放一個損毀的 `.dep` 後啟動，檢查無效檔案對話框及其兩個選項。
- 沒有選單、對話框或字串變更，因此本任務不需要截圖，也不需要執行 `generate-pot.bat`。

## 不在範圍內

- 把 `documents/workspace.py` 拆成 `documents/package.py` 與 `documents/batch.py`，以及把兩個 `choose_selection_after_delete` 合併為 `shared/selection.py`（S-6 其餘部分，屬 P2 層級）。
- 上述既有缺陷。
- `ExportCoordinator`、`ConversionPresenter`、`_show_file_error` 未使用的 `parent` 參數（M-9），以及 `gui` 中未使用的 `ConversionStageError` import（都屬 P1-4 範圍）。
- 把 `ApplicationPaths` 注入 `BrailleFrame`（P2-6）。服務已經以參數接收目錄。
- 調整 `_initialize_frame` 與 `_create_main_layout` 的順序，讓 `document_list` 防禦也消失。
- 把 controller 的屬性改為私有或唯讀。
- 縮排變更（P2-8）。
