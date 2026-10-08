# 設定檔對齊（P0-1）設計

## 目標

讓 `client/config.py` 與其測試重新一致，並停止靜默吞掉 I/O 錯誤。本項對應 `storage/refactor.md` 第 6.1 節路線圖的 P0-1，涵蓋發現 S-5（3.1 節）、5.3 節（錯誤處理）中的 `config.py` 項目，以及 5.4 節（死 setter）中的 `config.py` 項目。

三項變更：

1. 修正 `tests/test_translation_settings.py::test_save_persists_one_complete_settings_value` 過時的預期值。該測試改為預期 `_save_to_file` 刻意寫入新設定檔的 `language_detection.charset_maps` 預設值。注入行為本身保留（見「決策」）。
2. `_load_from_file` 與 `_save_to_file` 透過專案 logger 記錄失敗，不再隱藏錯誤。
3. 移除未使用的 setter：`set_view_font_size`、`set_view_scheme`、`set_braille_font`。

這是重建安全網的小步驟，不包含 S-5 建議的 `ConfigStore` 重新設計。

## 決策

- **不採納路線圖移除 `language_detection` 注入的建議。** `storage/refactor.md`（S-5 與 P0-1 列）以「讀取端已合併預設值」為由，提議刪除 `_save_to_file` 中把 `language_detection.charset_maps` 預設值寫入新設定檔的區塊。但這個注入是最近一次功能 commit `6e5819f`（「feat: align language detection with configured language」）刻意加入的，該 commit 也新增了 `test_new_config_file_contains_language_detection_defaults` 來固定此行為。它是使用者可見的：新的 `config.json` 會顯示 `charset_maps` 區段，這是使用者發現並手動編輯此設定的唯一途徑（沒有 UI 可編輯）。重構必須保留使用者可見行為，因此保留注入。錯的是那個失敗的測試：`6e5819f` 沒有更新 `tests/test_translation_settings.py`，所以 P0-1 讓該測試對齊目前行為，而不是修改 `config.py` 去配合測試。
- 兩個 I/O 輔助函式的捕捉範圍維持 `except Exception`（不在未捕捉例外的 GUI 處理器中產生新的當機路徑）；縮小範圍留待 S-5 的 `ConfigStore` 工作。

## 現況（2026-10-08 於 `refactor/p0-1-config-alignment`、HEAD `6e5819f` 驗證）

- `config.py` 使用 4 個空白縮排，不是 tab，請維持 4 個空白。
- `_load_from_file`（47–54 行）遇到 `FileNotFoundError` 回傳 `{}`，遇到其他任何 `Exception`（JSON 損毀、`UnicodeDecodeError`、`PermissionError` 等）也回傳 `{}`，且完全不回報。
- `_save_to_file`（57–70 行）在 `CONFIG_PATH` 尚不存在時，於資料最前面加入 `{"language_detection": {"charset_maps": DEFAULT_CHARSET_MAPS}}`（59–65 行），整個寫入過程包在 `except Exception: pass`（69–70 行）裡。
- 該注入由 commit `6e5819f`（「align language detection with configured language」）加入。同一個 commit 也修改了 `tests/test_config.py` 使其預期注入，包括 `test_new_config_file_contains_language_detection_defaults`，但沒有更新 `tests/test_translation_settings.py`。因此 `test_save_persists_one_complete_settings_value` 目前失敗，是基線的 2 個已知失敗之一（完整測試：428 個，failures=2，skipped=7）。
- `get_charset_maps()`（123–128 行）透過 `_get_dict_setting` 讀取，而它本來就會把 `DEFAULT_CHARSET_MAPS` 與已儲存的值合併。因此把預設值寫進檔案，不會改變呼叫端拿到的結果。
- 轉換期間，`languageDetection/__init__.py:365` 會呼叫 `config.get_charset_maps()`，`pipeline.py:79` 與 `languageDetection` 會呼叫 `config.get_lang()`，兩者每次呼叫都重新讀檔（app 中沒有任何地方呼叫 `set_lang`，所以 `_runtime_lang` 永遠未設定）。設定檔損毀時，`_load_from_file` 內的 log 呼叫在每次轉換中會執行很多次。
- 死 setter，以 `grep -rn` 搜尋整個儲存庫（`*.py`）確認：
  - `set_view_font_size`（184 行）：`config.py` 以外，只有 `tests/test_config.py:22` 呼叫。`gui.py:849` 定義的是另一個無關的方法 `BrailleFrame._set_view_font_size`，它走 `settings.view.save_view_settings`。
  - `set_view_scheme`（194 行）：只有 `tests/test_config.py:23`。
  - `set_braille_font`（204 行）：只有 `tests/test_config.py:122`。
  - app 只透過 `set_view_settings`（由 `settings/view.py` 呼叫）儲存檢視設定。
- logging 慣例：各模組以 `log.get_logger(name, filename, level)` 取得 logger，例如 `dotexpress.translation` 與 `translation.log`，層級 `WARNING`。該 `FileHandler` 使用 `delay=True`，所以 import 模組既不會開檔，也不會建立 `log/`。`tests/test_log.py` 涵蓋此行為，2026-07-20 應用程式資料路徑 spec 也要求如此。

## 行為變更

### 1. 保留 `language_detection` 注入；修正過時的測試

`_save_to_file` 的 `if not os.path.exists(CONFIG_PATH): data = {...}` 區塊維持不變。新建立的設定檔仍以 `{"language_detection": {"charset_maps": DEFAULT_CHARSET_MAPS}}` 開頭，後面接著 setter 寫入的區段。路線圖的移除提議為何不採納，請見「決策」。

此項唯一的變更在 `tests/test_translation_settings.py`：`test_save_persists_one_complete_settings_value` 的預期 dict 在既有的 `conversion` 區段旁加入 `"language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS}`，與 `tests/test_config.py` 已經預期注入的方式一致。

### 2. 記錄讀寫失敗，而不是吞掉

在 `config.py` 新增模組層級 logger：

```python
import logging
from log import get_logger

logger = get_logger("dotexpress.config", "config.log", level=logging.WARNING)
```

- 此做法沿用既有的各模組慣例。`delay=True` 的 file handler 讓 import `config` 時不建立任何檔案或目錄。第一筆記錄才會開啟 `<application-root>/log/config.log`。`gui.BrailleApp.OnInit` 會在任何正常設定讀取之前驗證並建立 `log/`。
- `log` 只 import `logging`、`pathlib` 與 `app_paths`，而 `config` 本來就 import `app_paths`，不會新增 import 循環。
- log 訊息是給開發者的英文診斷資訊，不經 gettext，不需要修改 `.po`/`.mo`。

`_save_to_file(data)`：

- 保留 `except Exception`（捕捉範圍與現在相同）。在處理區塊中呼叫 `logger.exception("Failed to save config file %s", CONFIG_PATH)`，以 ERROR 層級記錄並附上 traceback。函式仍回傳 `None`，不會拋出例外。
- 每次失敗都記錄，不去重。儲存由使用者觸發（設定對話框、字典選擇），或在啟動時發生一次（`get_or_create_client_id`），所以量很小。每次遺失的寫入都值得記錄。
- 絕不記錄設定資料本身，因為其中可能含有 client id。

`_load_from_file()`：

- `FileNotFoundError` 仍回傳 `{}`，不記錄任何東西。首次執行時檔案不存在是正常的。
- 其他任何 `Exception` 仍回傳 `{}`，並另外記錄一筆 WARNING（app 退回預設值），附 `exc_info=True`，訊息為 `"Failed to read config file %s; using defaults"`，參數為 `CONFIG_PATH`。
- 為了避免「現況」所述的每次呼叫都讀檔而灌爆 log，對警告做節流。保留一個模組層級的 `dict[str, str]`，將設定檔路徑對應到上一次已記錄失敗的簽章（`f"{type(error).__name__}: {error}"`）：
  - 失敗時，只有在該路徑沒有紀錄、或簽章不同時才記錄，接著存入該簽章。
  - 成功讀取或遇到 `FileNotFoundError` 時，移除該路徑的紀錄。之後檔案若再次損毀，會再記錄一次。
  - 不加鎖。單一 dict 操作在 GIL 下是原子的。執行緒競爭時（`client_init` 在背景執行緒執行），最壞情況是多一筆重複警告。
- 不改變對解析結果的驗證。頂層 JSON 值若不是物件（例如 `[]`），仍原樣回傳。這是另一個既有缺陷，不在本次範圍內，已列於「不在範圍內」。

### 3. 移除死 setter

從 `config.py` 刪除 `set_view_font_size`、`set_view_scheme`、`set_braille_font`。保留 `set_view_settings` 與三個檢視 getter（`get_view_font_size`、`get_view_scheme`、`get_braille_font`），因為 `settings/view.py` 會使用它們。

路線圖的 P0-3 也列了這三個 setter（5.4 節）。P0-1 合併後它們已不存在，P0-3 只需確認即可。

## 維持不變的部分

- `_save_to_file` 建立新設定檔時注入 `language_detection.charset_maps` 預設值的行為，以及 `get_charset_maps()` 回傳的值。
- `config.py` 中所有保留下來的公開函式與常數，其簽章、預設值與回傳值。
- `_load_from_file` 與 `_save_to_file` 永遠不會拋出例外。呼叫端（GUI 事件處理器、`client_init` 背景執行緒）看到的仍是同樣不拋例外的行為。
- read-modify-write 語意，包括保留未知或其他區段。
- 寫入機制：非原子性的 `open(..., "w")` 加上 `json.dump(..., ensure_ascii=False, indent=2)`，以及對父目錄的 `os.makedirs(..., exist_ok=True)`。
- `config.CONFIG_PATH` 仍是在呼叫時才讀取的模組屬性，測試仍可 monkeypatch。
- 檔案不存在或損毀時，getter 的既有結果（退回預設值）。
- 沒有任何使用者可見字串變動，GUI 也不會因這些 log 紀錄而顯示任何東西。

## 不在範圍內

- `ConfigStore` repository、把 `save_translation_settings` 合併為單次寫入、移除 `_runtime_lang`/`set_lang`（S-5 後續階段）。
- 原子寫入，以及防止損毀的檔案被下一次 setter 覆寫。目前損毀的檔案會讀成 `{}`，下一次儲存會以單一區段覆蓋它。這點維持不變，新的警告讓它變得可見。
- 拒絕頂層不是物件的 JSON 值。
- 縮小 `except Exception` 的捕捉範圍。
- 5.3 或 5.4 節中 `config.py` 以外的其他項目。

## 測試策略

所有測試都用 `unittest`，從 `client/` 執行，並沿用既有的 `setUp`，把 `config.CONFIG_PATH` 指向暫存目錄。

`tests/test_translation_settings.py`

- 只更新 `test_save_persists_one_complete_settings_value` 的預期 dict，加入 `"language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS}`。如此該測試即可在注入不變的情況下通過。

`tests/test_config.py`

- 既有的注入預期維持不變：完全相等比對之預期 dict 中的 `"language_detection": {...}` 項目，以及 `test_new_config_file_contains_language_detection_defaults`，都照原樣保留。
- 將使用已刪除 setter 的測試改用 `set_view_settings`：
  - `test_view_settings_are_persisted_under_view_section` 呼叫 `set_view_settings(18, "dark", "simbraille")`，並預期三個檢視鍵都存在（加上既有的 `language_detection` 項目）。
  - 點字字型儲存測試驗證 `set_view_settings` 會把 `braille_font` 寫在 `view` 底下，且保留其他區段中不相關的鍵。
- 新增錯誤處理測試：
  - **儲存失敗會記錄、不會拋出。** 把 `CONFIG_PATH` 指到一個路徑元件是一般檔案的位置之下，這樣 `os.makedirs` 在所有平台上都會拋出 `OSError`。在 `self.assertLogs("dotexpress.config", level="ERROR")` 中呼叫一個 setter，並驗證：
    - 沒有例外；
    - 有一筆紀錄包含設定檔路徑；
    - 沒有建立設定檔。
  - **損毀的檔案只記錄一次並回傳預設值。** 寫入無效 JSON。在 `assertLogs(..., level="WARNING")` 中呼叫兩個不同的 getter，並驗證：
    - 兩者都回傳預設值；
    - 只產生一筆警告。
  - **恢復後會再次發出警告。** 依序使用損毀檔、有效檔、再損毀檔，預期總共兩筆警告。
  - **檔案不存在時保持安靜。** patch `config.logger`（例如用 `unittest.mock.patch.object`），驗證沒有記錄任何東西。不要使用 `assertNoLogs`：它需要 Python 3.10 以上，而本次未驗證 Windows 建置用直譯器的最低版本。
- `assertLogs` 會在區塊執行期間替換 logger 的 handler，所以這些測試不會把 `config.log` 寫進真實的應用程式 log 目錄。

必須維持全綠、內容不變的既有安全網：`tests/test_view_settings.py`、`tests/test_translation_tables.py`、`tests/test_log.py`、`tests/test_app_paths.py`、`tests/test_settings_state.py`、`tests/test_language_detection_char_langinfo.py`。

## 驗收條件

1. `config.py` 中的 `language_detection` 注入維持不變，且 `grep -rn "set_view_font_size\|set_view_scheme\|set_braille_font" client --include=*.py` 只找到 `gui.py` 的 `_set_view_font_size` 方法與其呼叫處。
2. `_load_from_file` 與 `_save_to_file` 中沒有裸 `pass`。所有非 `FileNotFoundError` 的失敗都依上述方式經由 `config.logger`（`dotexpress.config`）記錄。
3. import `config` 不會建立 `log/` 或 `config.log`。這由 `log.get_logger` 保證，並由 `tests/test_log.py` 涵蓋。
4. 聚焦驗證通過，0 個失敗、0 個錯誤：
   `cd client && python3 -m unittest tests.test_config tests.test_translation_settings tests.test_view_settings tests.test_translation_tables tests.test_log tests.test_app_paths -v`
5. 完整測試：`cd client && python3 -m unittest discover -s tests -p "test_*.py"` 回報 `failures=1`（只剩已知的 P2-5 `test_conversion_service` 失敗）、`errors=0`、`skipped=7`，測試數為 428 加上新增測試數。
6. 本 Linux 主機無法驗證：Windows 打包後的行為。logging 走的是 `gui`、`client_init` 與 translation provider 在 Windows 上已在使用的同一條 `log.get_logger` 路徑，且沒有任何 Windows 專屬程式碼變更。

## 風險

- **與路線圖列的差異**（低）：P0-1 不移除 `storage/refactor.md` 提議移除的注入。後續任務（特別是 S-5 的 `ConfigStore` 工作）必須保留注入，而不是照原始建議處理；「決策」一節即為此紀錄。
- **設定檔損毀時灌爆 log**（已緩解）：以路徑加簽章為鍵的節流處理。
- **`log/` 存在前就記錄**（低）：若在 `prepare_application_directories` 執行前讀取或儲存設定失敗（例如 `main.py` 等非 GUI 進入點，或新 clone 在沒有 `client/log/` 的情況下執行測試），或 `log/` 無法寫入，`FileHandler` 便無法開檔。在 `delay=True` 下，`logging.FileHandler.emit` 是在其 `try`/`handleError` 區塊之外呼叫 `self._open()`，因此 `FileNotFoundError`/`PermissionError` 會從 logging 呼叫中拋出，`Handler.handleError` 不會攔下。因應方式（見 plan 的 Spec Correction）：兩處記錄都經由 `_log_current_exception`，當 logging 呼叫拋出 `OSError` 時丟棄該筆記錄，因此 `_load_from_file` 與 `_save_to_file` 仍然絕不拋出例外；此時該筆診斷資訊會遺失。在正常 GUI 啟動順序中，`log/` 會在主視窗讀取設定前完成驗證。
- **測試寫入真實 log 目錄**（低）：只有在未來的測試觸發失敗路徑、卻沒有使用 `assertLogs` 或 patch logger 時才可能發生。測試策略要求兩者擇一。
- **與 P0-3 重疊**（功能上無影響）：P0-3 必須略過 P0-1 已移除的三個 setter。
