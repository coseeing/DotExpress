# 翻譯表 Frame 狀態（P0-2）設計

## 目標

把目前使用中的翻譯表對應，從模組層級的可變全域變數 `gui.language_map_translate_table` 移到 `BrailleFrame` 的實例狀態，並把兩處相同的「未選擇預設翻譯表」檢查合併成一個輔助方法。本項對應 `storage/refactor.md` 第 6.1 節路線圖的 P0-2，涵蓋發現 D-2（3.5 節，DIP）以及 5.2 節（全域狀態）中的 `gui.py:230` 項目。

這是保持行為不變的重構。使用者可見行為、字串與已儲存的資料都不變。

## 現況（2026-10-08 於 `refactor/p0-2-translation-tables-state`、HEAD `506a8da` 驗證，P0-1 已合併）

`client/gui.py` 使用 tab 縮排；`client/tests/test_gui_document_flows.py` 使用 4 個空白。

該全域變數的所有讀寫位置（對整個儲存庫的 `*.py` 執行 `grep -rn language_map_translate_table`）：

| 位置 | 作用 |
| --- | --- |
| `gui.py:230` | 模組匯入時建立：`language_map_translate_table = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()`。這會在 `import gui` 時讀取 `config.json`，早於 `BrailleApp.OnInit` 準備應用程式目錄。 |
| `gui.py:622`（`get_settings_snapshot`） | 把全域變數傳給 `DotExpressSettingsSnapshot.create`，後者以 `dict(...)` 複製。 |
| `gui.py:637-638`（`apply_settings_from_dialog`） | 在 `tables = dict(snapshot.translation_tables)` 之後，以 `clear()` + `update(tables)` 就地修改全域變數，再由 `save_translation_tables(tables)` 寫回設定檔。 |
| `gui.py:790`（`_build_conversion_request`） | `translation_tables=language_map_translate_table.copy()`，讓背景轉換工作取得自己的副本。 |
| `gui.py:1529-1535`（`_start_export_conversion`） | `default_table = ...get("default")`；若為 falsy，建立 `_("Please select a translation table first.")`，優先交給 `on_missing_table`，否則交給 `on_error`，兩者皆無則不處理；回傳 `False`。 |
| `gui.py:1609-1617`（`on_convert`） | 相同的 `get("default")` 檢查；若為 falsy，顯示 `wx.MessageBox(<同一訊息>, _("Info"), wx.OK \| wx.ICON_INFORMATION, parent=self)` 後返回。 |
| `tests/test_gui_document_flows.py:1087, 1129` | 兩個「缺少翻譯表」匯出測試中的 `patch.dict(gui.language_map_translate_table, {"default": ""}, clear=True)`。 |
| `tests/test_gui_document_flows.py:1161` | `test_apply_settings_from_dialog_updates_all_live_state` 對全域變數做斷言，但沒有還原，導致該測試行程剩下的時間內全域變數都是 `{"default": "en-ueb-g1.ctb", "math": "Nemeth"}`（測試間狀態外洩）。 |

沒有其他模組或測試匯入或 patch 這個全域變數。`client/main.py` 直接使用 `config.DEFAULT_TRANSLATION_TABLES`，不受影響。`docs/` 下較舊的文件（`2026-07-06-*` 的 spec 與 plan、`docs/refactor/refactor4.md`、history）提到這個名稱；它們是歷史紀錄，不修改。

相關事實：

- `settings.translation_tables.load_translation_tables()` 回傳 `dict(config.get_translation_tables())`。`config._get_dict_setting` 一定會把已儲存的字串值合併到 `DEFAULT_TRANSLATION_TABLES` 上，因此結果永遠不會是空的，`or DEFAULT_TRANSLATION_TABLES.copy()` 的後備在實務上不可能觸發。不過已儲存的值仍可能是 `""`（例如手動編輯成 `"default": ""`），因為合併會接受任何 `str`。
- 設定對話框（`settings/dialogs.py` 的 `TranslationTablesPanel`）只讀寫 `snapshot.translation_tables`。它的 `is_valid`/`validation_error` 會拒絕儲存空的 `default` 或 `math`。非字串的已儲存值會在合併時被丟棄並退回預設翻譯表。因此 `gui.py` 的「未選擇預設翻譯表」防護只會在 `config.json` 含有 `"default": ""`（手動編輯或舊版程式寫入）時觸發。它是防護而不是死碼，必須保留。
- `DotExpressSettingsSnapshot`（`settings/state.py`）是 frozen dataclass，在 `create`、`with_translation_tables` 與 `copied` 時都會複製 `translation_tables`。對話框透過 `BrailleFrame.apply_settings_from_dialog` 提交，並以回傳的 snapshot 重新載入各面板。
- Frame 本來就以一般實例屬性保存另外兩組設定：`self.translation_settings`（在 `_initialize_state` 設定）與 `self.view_settings`。在 `apply_settings_from_dialog` 中，它們是被重新指派，而不是就地修改。
- 轉換在工作執行緒（`ConversionJobRunner`）上執行。request 拿到的是翻譯表的副本，因此之後的設定變更不會影響執行中的工作。
- 測試以 `BrailleFrame.__new__` / `object.__new__` 建立 frame，只設定所需屬性；測試中從不執行 `__init__` 與 `_initialize_state`。
- 基線：`tests.test_gui_document_flows` 執行 50 個測試，OK。完整測試：439 個，`failures=1`（已知的 P2-5 `test_conversion_service` 失敗），`skipped=7`。

## 設計

### 擁有權

由 `BrailleFrame` 以 `self.translation_tables: dict[str, str]` 擁有目前使用中的對應，與 `translation_settings`、`view_settings` 並列。

- 在 `_initialize_state` 中、緊接 `self.translation_settings = load_translation_settings(...)` 之處初始化，使用與現在相同的運算式：`load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()`。保留那個不可能觸發的後備，讓本變更不碰後備行為與 import。
- 刪除模組層級的 `language_map_translate_table`。`gui` 不再於匯入時為了翻譯表讀取 `config.json`。
- 此屬性視為「只替換」：程式碼指派新的 dict，絕不就地修改既有的 dict。這與另外兩個設定屬性遵循的規則相同。

不採用路線圖的另一個選項（改存 `self.settings_snapshot`）：那會同時改變 `translation_settings` 與 `view_settings` 的擁有方式，超出範圍，且牽動更多呼叫點。

### 設定變更的傳遞

`apply_settings_from_dialog` 改為替換參考，不再就地修改：

```python
tables = dict(snapshot.translation_tables)
self.translation_settings = translation
self.view_settings = view
self.translation_tables = tables
```

敘述順序、儲存呼叫（`save_translation_settings`、`save_translation_tables(tables)`、`save_view_settings`）與回傳值 `DotExpressSettingsSnapshot.create(translation, tables, view)` 都不變。因為 `create` 會複製，回傳的 snapshot 永遠不會與 frame 狀態共用同一個物件。

讀取端：

- `get_settings_snapshot` 傳入 `self.translation_tables`（與現在一樣由 `create` 複製）。
- `_build_conversion_request` 傳入 `self.translation_tables.copy()`。保留複製：工作執行緒必須擁有自己的 dict，轉換流程也不能修改 frame 狀態。

### 合併的預設翻譯表檢查

新增一個同時負責檢查與訊息的 frame 方法：

```python
def _missing_default_table_message(self) -> str | None:
	if self.translation_tables.get("default"):
		return None
	return _("Please select a translation table first.")
```

- `_start_export_conversion`：`message = self._missing_default_table_message()`；若不是 `None`，與現在完全相同地交給 `on_missing_table`，否則交給 `on_error`，並回傳 `False`。
- `on_convert`：同樣呼叫；若不是 `None`，顯示相同的 `wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)` 後返回。
- 真假判斷不變（`get("default")` 為 falsy 即視為缺少：鍵不存在、`""`、`None`）。
- 字面值 `_("Please select a translation table first.")` 仍是直接的 `_()` 呼叫，因此 gettext 擷取與既有的 `.po` 項目不受影響。該字串在 `gui.py` 中由兩次變成一次。

命名：路線圖建議 `_require_default_table() -> str | None`。這個名稱看不出回傳的字串是翻譯表還是錯誤訊息。本輔助方法回傳訊息，因為兩個呼叫端都需要訊息，而且都沒有使用翻譯表名稱。這只是命名上的偏離。

兩個呼叫端的區域變數 `default_table` 隨之移除；沒有其他地方使用它。

## 維持不變的部分

- 所有使用者可見行為：缺少翻譯表的訊息文字、`on_convert` 中的 `Info` 對話框、`_start_export_conversion` 的回呼分派順序（`on_missing_table` 優先於 `on_error`）與回傳 `False`，以及批次匯出逐檔累積失敗、不逐檔跳出訊息框的行為。
- Frame 的初始值（相同載入函式、相同後備）、設定對話框顯示的內容、儲存的內容與儲存時機。
- `ConversionRequest.translation_tables` 的內容，以及每個 request 都拿到獨立副本。
- `settings/state.py`、`settings/dialogs.py`、`settings/translation_tables.py`、`config.py` 與 conversion 套件都不修改。
- 不變更 `.po`/`.mo`：沒有新增、刪除或修改任何使用者可見字串。

唯一可觀察到的差異是時機：翻譯表改在建構 `BrailleFrame` 時（在 `BrailleApp.OnInit` 中、`prepare_application_directories` 之後）從 `config.json` 讀取，而不是在匯入 `gui` 時。兩個時間點之間沒有任何程式寫入翻譯表，所以讀到的值相同。設定檔讀取失敗的 log 現在會在 `log/` 存在之後才寫入，這是改善。

## 測試變更（`client/tests/test_gui_document_flows.py`）

Patch 點從模組全域變數改為 frame 屬性：

- `_make_frame` 設定 `frame.translation_tables = dict(gui.DEFAULT_TRANSLATION_TABLES)`，讓測試 frame 預設就像真正的 frame。
- `test_export_all_missing_table_accumulates_failures_without_per_file_message_boxes` 與 `test_single_pending_export_missing_table_shows_one_error_dialog_and_does_not_write_output`：移除 `patch.dict(gui.language_map_translate_table, ...)` context，改在呼叫前設定 `frame.translation_tables = {"default": ""}`。其他斷言不變。
- `test_apply_settings_from_dialog_updates_all_live_state`：斷言 `frame.translation_tables == snapshot.translation_tables` 且 `frame.translation_tables is not snapshot.translation_tables`。這同時消除了測試間的狀態外洩。

新增測試（同一檔案、相同 stub 設定）：

1. **全域變數已移除：** `self.assertFalse(hasattr(gui, "language_map_translate_table"))`。
2. **初始化：** `_initialize_state` 由 `load_translation_tables()` 設定 `translation_tables`，載入函式回傳 `{}` 時退回 `DEFAULT_TRANSLATION_TABLES`。Patch `_initialize_state` 呼叫的協作者（`get_dictionary_directory`、`ensure_default_dictionary`、`list_dictionary_names`、`load_translation_settings`、`get_workspace_directory`、`load_view_settings`、`load_translation_tables`，以及 frame 的 `_refresh_dictionary_names` / `_register_output_font`），確保不碰到真正的目錄或設定檔。
3. **Snapshot 讀取 frame 狀態：** `get_settings_snapshot` 回傳的翻譯表與 `frame.translation_tables` 相等，但不是同一個物件。
4. **Request 複製 frame 狀態：** `_build_conversion_request(...).translation_tables` 與 `frame.translation_tables` 相等，但是不同物件。
5. **傳遞：** 執行 `apply_settings_from_dialog(snapshot)`（patch 掉儲存）之後，`_build_conversion_request` 帶有新的翻譯表。
6. **輔助方法：** `_missing_default_table_message()` 對 `{"default": "zh-tw.ctb"}` 回傳 `None`，對 `{}`、`{"default": ""}`、`{"default": None}` 回傳翻譯後的訊息。
7. **`on_convert` 防護：** 在 `{"default": ""}` 時，呼叫一次 `wx.MessageBox`，參數為該訊息、`_("Info")`、`wx.OK | wx.ICON_INFORMATION`、`parent=frame`，且不呼叫 `_start_conversion`。已設定預設翻譯表時，呼叫一次 `_start_conversion` 且不顯示訊息框。
8. **匯出正常路徑：** 已設定預設翻譯表時，`_start_export_conversion` 回傳 `True`，並以 `update_output=False, show_success=False` 呼叫 `_start_conversion`。

其他測試檔不變。`tests/test_settings_dialogs.py`、`tests/test_settings_state.py`、`tests/test_translation_tables.py` 與 `tests/test_conversion_jobs.py` 作為未修改的安全網，須維持全綠。

## 驗收條件

1. `grep -rn "language_map_translate_table" client --include=*.py` 恰好只回傳一行：`client/tests/test_gui_document_flows.py` 中的防護測試 `self.assertFalse(hasattr(gui, "language_map_translate_table"))`（該測試必須寫出屬性名稱）。`grep -rn "language_map_translate_table" client --include=*.py | grep -v "^client/tests/"` 沒有任何結果。
2. `grep -n 'Please select a translation table first' client/gui.py` 恰好回傳一行，位於 `_missing_default_table_message` 內。
3. `BrailleFrame` 只讀取與替換 `self.translation_tables`；沒有任何程式呼叫 `clear()`/`update()` 或以其他方式就地修改它。
4. 聚焦驗證以 0 failures、0 errors 通過：
   `cd client && python3 -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_settings_state tests.test_translation_tables tests.test_conversion_jobs -v`
5. 完整測試：`cd client && python3 -m unittest discover -s tests -p "test_*.py"` 回報 `failures=1`（只有已知的 P2-5 失敗）、`errors=0`、`skipped=7`，測試數為 439 加上新增測試。
6. `client/locales/` 沒有任何變更。
7. 無法在此 Linux 主機驗證：Windows 上真正的 wxPython app（開啟設定、變更翻譯表、轉換、匯出）。本變更不碰任何 Windows 專屬程式碼，wx 呼叫也不變。

## 風險

- **有路徑在 `_initialize_state` 設定前就讀取 `self.translation_tables`**（低）：`__init__` 在建立版面、轉換狀態與事件繫結之前就執行 `_initialize_state`，所以不會有處理器更早觸發。繞過 `__init__` 的測試由 `_make_frame` 取得此屬性或自行設定。在真正的 wxPython frame 上，缺少屬性會直接引發 `AttributeError`；但在測試用的 wx stub 下不會：stub 的 `wx._Widget.__getattr__` 對任何不存在的屬性都回傳一個空操作函式，因此錯誤會晚一步才出現（`.get`/`.copy` 引發 `AttributeError: 'function' object has no attribute ...`、`DotExpressSettingsSnapshot.create` 中的 `dict(function)` 引發 `TypeError`，或呼叫尚未定義的方法時靜默回傳 `None`）。本規格中的測試在其依賴的每種情況下仍會明確失敗，只是實作前預期的失敗是斷言失敗，而非 `AttributeError`。
- **執行緒安全**（不變）：工作執行緒拿到的是在 UI 執行緒建立的副本，frame 屬性也只在 UI 執行緒上被替換。
- **全域變數的隱藏外部使用者**（未發現）：grep 顯示 `gui.py` 與 `test_gui_document_flows.py` 以外沒有任何 import 或 patch。
- **與後續任務重疊**（低）：P0-3 及之後修改 `gui.py` 的任務都必須使用 `self.translation_tables`。P0-4 會把 wx stub 移出 `test_gui_document_flows.py`，但保留 `_make_frame`，因此在那裡設定的屬性預設值會延續。P0-5 會把 `_`/gettext 移到 `i18n.py`；只有 `_` 的 import 改變，輔助方法仍直接呼叫 `_()`。P2-6（注入 `ApplicationPaths`）之後可能會移動載入呼叫的位置；本文決定的擁有權仍然成立。

## 不在範圍內

- 在 frame 上保存整個 `DotExpressSettingsSnapshot`，或以其他方式統一三個設定屬性。
- 移除不可能觸發的 `or DEFAULT_TRANSLATION_TABLES.copy()` 後備。
- 驗證從 `config.json` 載入的翻譯表名稱或型別。
- 為測試抽出共用的 wx stub 模組（P0-4）。
- 修改提到舊全域變數的歷史文件。
