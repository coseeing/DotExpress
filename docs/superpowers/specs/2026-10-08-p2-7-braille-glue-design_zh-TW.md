# 點字膠水清理（P2-7）設計

## 目標

`storage/refactor.md`（第 6.3 節）的 roadmap 任務 P2-7，對應發現 D-6（「`braille/` 第一方膠水在 import 時呼叫 `logging.basicConfig`」），另加上 P1 階段 review（`docs/superpowers/history/2026-10-08-02-refactor-p1/review_task.md` 的「P2-7」段）交辦的兩項，以及 P2-6 交接時關於測試寫入 log 的備註。

完成後：

- import `braille.tables` 或 `braille.louis_helper` 不再設定 root logger。兩個模組都改用 `logging.getLogger(__name__)` 記錄。
- `braille.tables.get_table_directory(source)` 是查詢表格來源資料夾的公開方式。`louis_helper` 不再讀取 `braille_tables._tablesDirs`。
- 翻譯 runtime provider 建立 `MathCATAdapter`、把它往下傳給數學鏈，並在 runtime 關閉時關閉它。模組層級的 `_SHARED_ADAPTER`／`get_shared_mathcat_adapter()` 單例移除。
- `getDefaultTableForCurLang(tableType, lang)` 刻意保留（決策 D4）。
- 單元測試不再追加寫入真實的 `client/log/*.log`。

這是重構。不顯示也不朗讀任何新內容，msgid 不變（353 個，同一集合），轉換輸出相同，golden fixture 不變，`<root>/log/` 中的檔案收到相同的紀錄，DotExpress 不擁有的 NVDA 衍生檔（`client/braille/tables/__tables.py`、`client/braille/liblouis/__init__.py`、`vendor/nvda/` 中除了改寫後 helper 之外的一切）都不動。唯一可觀察的差異在**原始碼執行**時的主控台（打包版以 `--noconsole` 建置，沒有主控台）：見 D2。

## 關鍵發現：`louis_helper.py` 是產生出來的檔案

Roadmap 把 `client/braille/louis_helper.py` 列為要修改的檔案，而 `storage/refactor.md` 第 7 節第 6 點要求先確認 `scripts\sync-nvda.py` 是否會覆蓋它，若會，就改 adapter 層。結果是會：

- `client/braille/louis_helper.py` **未納入版控**。`client/.gitignore:13` 忽略它，`scripts/clean-liblouis.bat:44` 與 `sconstruct` 的 `_remove_liblouis_artifacts` 會刪除它，`readme.md`（「The generated runtime outputs are ...」）也說它不可手改。
- 它分兩步產生。`scripts/sync-nvda.py` 的 `_adapt_helper()`（144-200 行）以一組固定的字串替換改寫 NVDA 的 `include/nvda/source/louisHelper.py`，結果寫到已納入版控的 `vendor/nvda/liblouis/runtime/louis_helper.py`。接著 `scons install`（`scripts\install.bat`）經由 `vendor/nvda/liblouis/dist/` 把它複製到 `client/braille/louis_helper.py`（`sconstruct` 94-109 行）。
- 在此 checkout 上確認：`_adapt_helper(include/nvda/source/louisHelper.py)` 與 `vendor/nvda/liblouis/runtime/louis_helper.py` 以及本機的 `client/braille/louis_helper.py` 逐位元組相同。
- `logging.basicConfig(...)` 呼叫和 `braille_tables._tablesDirs.get(...)` 那一行都是 `_adapt_helper` 插入的（166 行 `"from logHandler import log\n"` 的替換，以及 175 行的替換）。NVDA 原始碼兩者皆無。

所以修改落在 DotExpress 擁有的程式碼：`_adapt_helper` 中的替換字串。NVDA 的檔案不動。已納入版控的快照 `vendor/nvda/liblouis/runtime/louis_helper.py` 只用 `_adapt_helper` 重新產生（決策 D3），被忽略的 `client/braille/louis_helper.py` 則由一般的 Windows 建置（`scripts\install.bat`）更新。最後這一步無法在這裡執行（Windows 待驗證項目）。

第二個發現（既有問題，不修）：**完整執行 `sync-nvda.py` 並非冪等。** 把 `synchronize()` 跑進一個連結到真實 `include/` 的暫存根目錄，產出與 `vendor/nvda/` 相同，唯獨 `vendor/nvda/liblouis/build/sconscript` 不同：commit `9aa8355` 與 `1bd19d7` 在最後一次 sync 後手動修改了它（`buildDir`、`workDir`、`buildInputsDir`）。完整 sync 會把這些修改還原，儘管 `AGENTS.md` 與 `readme.md` 都說重建前要重跑 sync。本任務不得執行完整 sync。列為後續事項。

## 現況（2026-10-08 於 `refactor/p2-7-braille-glue` 確認，HEAD `5764ad3`，已合併 P0-*、P1-*、P2-1..P2-4 與 P2-6）

`$SP` 為本次 session 的 scratchpad，`$PY` 為 `$SP/venv/bin/python`。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1071 tests`、`FAILED (failures=1, skipped=9)`。失敗的是 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。`$PY $SP/shuffle_harness.py 1` 結果相同。在 repo 根目錄，`$PY -m unittest discover -s scripts/tests` 得到 `Ran 25 tests ... OK`。`$PY $SP/p12/tools/msgid_scan.py client` 回報 `source msgids: 353`。Fixture sha256：`client/tests/fixtures/translation_golden.json` 為 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`，`client/tests/fixtures/dictionary_entries_trace.json` 為 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`。

給要 grep 的人：此環境的 shell `grep` 會略過被忽略的檔案，所以看不到 `client/braille/louis_helper.py`。請用 `command grep`。

### 誰設定 logging

| 位置 | 內容 |
| --- | --- |
| `client/braille/tables/__init__.py:24-31`（tab、**CRLF**） | `import logging`、`log = logging`（模組本身，不是 logger）、`log.basicConfig(level=INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt=...)`。第一次 import 時執行。`addTable`（127-165）呼叫兩次 `log.warning(...)`，因此這些是模組層級的 `logging.warning` 呼叫；若 root 沒有 handler，它們會自己再執行一次 `basicConfig()`。 |
| `client/braille/louis_helper.py:19-26`（產生檔、tab、LF） | `log = logging.getLogger(__name__)`，接著同樣的 `logging.basicConfig(...)`。 |
| `client/log.py:11-32` | `get_logger(name, filename, level)`：每個 logger 一個 `FileHandler(<root>/log/<file>, delay=True)`、明確的 level、`propagate = False`。 |
| `get_logger` 的使用者 | `config.py:13`（`config.log`）、`client_init.py:16`（`init.log`）、`gui.py:97`（`gui.log`）、`ui/dual_view.py:13`（`dual_view.log`）、`adapters/translation/provider.py:13`（`translation.log`）、`conversion/math_service.py:10`（`math.log`）。 |

`client/`、`server/`、`scripts/` 中沒有其他模組呼叫 `basicConfig` 或碰 root logger（`command grep -rn basicConfig`、`logging.getLogger`）。測試從不設定 root logger。

在 Linux 上量測：`import braille.tables` 之前 root logger 沒有 handler、level 為 `WARNING`；之後有一個 `StreamHandler(<stderr>)`、level 為 `INFO`。import 時不會發出警告（`__tables.py` 沒有重複的語言項目）。

目前 root handler 的用途：每個 `get_logger` logger 都 `propagate = False`，所以 app 的 log 檔都不依賴它。會到達 root 的只有 DotExpress 沒設定的 logger：`braille.louis_helper`、`braille.tables` 中的 `logging.warning` 呼叫，以及第三方函式庫。在 app 中，`gui.py` 被 import 時 `settings/dialogs.py:10` 會 import `braille.tables`，因此 root 在 `OnInit` 之前就已被設定。打包版以 `--noconsole` 建置（`scripts/build-dotexpress.bat`），`sys.stderr` 為 `None`，root handler 的輸出被丟棄。只有原始碼執行（在主控台中 `python gui.py`）才會印出。

`louis_helper._isDebug()` 是 `log.isEnabledFor(logging.DEBUG)`。有 `basicConfig` 時有效 level 為 `INFO`；沒有時為 `WARNING`。兩者都高於 `DEBUG`，所以 liblouis 的 log callback 與 resolver 的 debug 訊息不論如何都保持關閉。

### `braille/tables/__init__.py`（tab、CRLF、251 行，每行都以 `\r\n` 結尾）

- `TABLES_DIR`（34）、`DEFAULT_TABLE`（39）、`TableSource`、`TableType`。
- `_tablesDirs`（57-61）：`ChainMap({TableSource.BUILTIN: TABLES_DIR})`，在 229 行重新綁定為 `_tablesDirs.new_child()`。`terminate()`（248-251）清除子 map。DotExpress 從不呼叫 `braille.tables.initialize()`／`terminate()`。
- `getDefaultTableForCurLang(tableType, lang)`（104-124）：P1-1 讓 `lang` 成為參數。整個 repo 沒有呼叫者。`tests/test_braille_tables_default_lang.py` 釘住它。`addTable` 會填 `_inputTableForLangs`／`_outputTableForLangs`，只有此函式會讀。
- `getTable`（168-175）、`listTables`（178-185；`settings/dialogs.py:543` 使用）。
- 上游 NVDA（`include/nvda/source/brailleTables/__init__.py`）同樣沒有 `_tablesDirs` 的公開存取函式。
- `sync-nvda.py` 不產生此檔或 `__tables.py`。

### `louis_helper` 的表格解析（產生檔，行號依目前輸出）

`_resolveTableInner(tables, base)`（49-81）：對每個名稱，若 `base` 為 `None`，嘗試 `braille_tables.getTable(name)` 與 `braille_tables._tablesDirs.get(registeredTable.source)`（65），遇到 `LookupError` 則退回；有 `base` 時先搜尋 `dirname(base)`；最後是 `TABLES_DIR`。`_resolveTable`（86-124）是 ctypes callback。`initialize()`（143-151）註冊 log callback、`LOG_DEBUG` 與 resolver；`terminate()`（154-162）撤銷它們並呼叫 `lou_free()`。

在正式環境中，`LiblouisTextTranslator.translate`（`adapters/translation/liblouis.py:28`）一律傳完整路徑（`os.path.join(tables_dir, table)`）。`getTable(完整路徑)` 會拋 `KeyError`，所以「已註冊來源」分支只有在裸檔名時才會走到：`tests/test_liblouis_runtime.py`（`_resolveTableInner(["en-ueb-g2.ctb"])`、`louis.translateString(["zh-tw.ctb"], ...)`）。被 include 的表格走 `base` 分支。

在 Linux 上 `import braille.liblouis` 會拋 `AttributeError`（隨附的 DLL 無法載入），所以這裡無法 import 真正的 helper。以假的 `braille.liblouis` 模組（`LOG_*` 常數、`LogCallback = ctypes.CFUNCTYPE(None, c_int, c_char_p)`、`fileSystemEncoding`）載入 `vendor/nvda/liblouis/runtime/louis_helper.py` 是可行的：在此 checkout 上它會在 root 加上 `INFO` 的 `StreamHandler`，並能把已註冊表格解析到其來源資料夾。新測試採用此法（雛形已確認）。

### MathCAT 生命週期

| 位置 | 內容 |
| --- | --- |
| `conversion/mathcat_adapter.py:20-100`（tab） | `@dataclass MathCATAdapter(resource_root, _libmathcat=None, _dll_directory_handle=None)`。`initialize()` 載入 `libmathcat_py.pyd`：`os.add_dll_directory(resource_root)` 一次（保留 handle，從不關閉）、以 `importlib` 載入、`sys.modules.setdefault("libmathcat_py", module)`。`get_braille_for_mathml(mathml, braille_code=None, *, language)` 每次呼叫都重設規則與偏好，並把非 `MathCATError` 的例外包成 `MathCATError`。沒有 `close()`。 |
| `conversion/mathcat_adapter.py:103-110` | `_SHARED_ADAPTER` 與 `get_shared_mathcat_adapter()`：以 `get_default_mathcat_resource_root()`（16-17，`client/mathcat/assets`，唯讀的隨附資源）建立的 process 層級 lazy 單例。 |
| `conversion/math_service.py:40-52`（tab） | `mathml_to_nemeth_braille(mathml, braille_code=DEFAULT, *, language)` 在函式內 import `get_shared_mathcat_adapter` 並呼叫單例。 |
| `conversion/math_service.py:55-73` | `translate_math_segment(latex, braille_code=DEFAULT, *, language)`：先 `latex_to_mathml` 再 `mathml_to_nemeth_braille`；任何例外都記到 `math.log` 並以 `MathConversionError` 拋出。 |
| `adapters/translation/mathcat.py`（4 空白） | `MathCATMathTranslator(*, translate_math)`：呼叫 `translate_math(source, braille_code=, language=)` 並建立單一 token 的 `TranslationResult`。沒有 `close()`。 |
| `adapters/translation/provider.py:85-100`（4 空白） | `create_default_math_translator(*, platform=None)`：非 `win32` -> `RuntimeUnavailableError`；否則 import、`get_shared_mathcat_adapter().initialize()`，把 `ImportError`／`OSError`／`MathCATError` 轉成 `RuntimeUnavailableError`，回傳 `MathCATMathTranslator(translate_math=translate_math_segment)`。 |
| `adapters/translation/provider.py:16-18, 30-60` | 當 translator 有可呼叫的 `close` 時，`build_translation_runtime` 把 `translator.close` 加為關閉 callback。目前只有 `LiblouisTextTranslator.close`（`helper.terminate()`）符合。 |
| `adapters/translation/contracts.py:158-170` | `TranslationRuntime.close()`：冪等，以反序執行 callback。 |
| `gui.py:1086-1096` | `OnExit`：清理 dual-view，然後 `runtime.close()`。`main.py:18-39`（demo）在 `finally` 中關閉 runtime。 |

也就是說，共用 adapter 在 Windows 上於建立 runtime 時產生，所有數學轉換都用它，從不關閉，其 DLL 目錄在整個 process 生命週期都保持註冊。單例的使用者：`provider.py:9, 96`、`math_service.py:46-48`、`tests/test_translation_runtime_provider.py:253`（patch `provider.get_shared_mathcat_adapter`）、`tests/test_math_service.py:31`（patch `conversion.mathcat_adapter.get_shared_mathcat_adapter`）。`translate_math_segment`／`mathml_to_nemeth_braille` 的呼叫者：只有 provider 與 `tests/test_math_service.py`。`tests/test_math_translation_adapter.py` 與 `tests/test_translation_golden.py:125` 也會建立 `MathCATMathTranslator(translate_math=...)`。

### 會寫入真實 log 檔的測試

逐一單獨執行每個測試模組，同時觀察 `client/log/*.log` 的大小。恰有四個會追加寫入真實檔案：

| 模組 | 檔案 | Logger |
| --- | --- | --- |
| `tests/test_client_init.py` | `init.log` | `dotexpress.client_init` |
| `tests/test_dual_view_frame.py` | `dual_view.log` | `dotexpress.dual_view` |
| `tests/test_math_service.py` | `math.log` | `dotexpress.math` |
| `tests/test_translation_runtime_provider.py` | `translation.log` | `dotexpress.translation` |

各模組在 import 建立 logger 時，handler 就綁定到 `<client>/log/`（P2-6 D10）。`client/log/` 被 git 忽略，所以 `git status` 看不到，但檔案每跑一次就變大（此處 math.log 已 1.9 MB）。

## 決策

| # | 決策 | 理由 |
| --- | --- | --- |
| D1 | `braille/tables/__init__.py`：把 `log = logging` + `log.basicConfig(...)` 換成 `log = logging.getLogger(__name__)`。其他每一行不動。 | `log = logging` 讓 `log.warning` 成為模組層級函式，root 沒有 handler 時它會自己呼叫 `basicConfig()`。只拿掉明確的呼叫，只會把 root 設定延後到第一個重複語言警告，而不是移除。具名 logger 保留相同的 `log.warning(...)` 呼叫點與訊息。 |
| D2 | 兩個膠水模組都不設定 logging。不加替代 handler（不加 `get_logger("dotexpress.liblouis", "liblouis.log")`）。 | App 的 log 檔只來自 `propagate = False` 的 `get_logger` logger，所以不變。打包版沒有主控台，所以不變。原始碼執行時，到達 root 的紀錄改由 Python 的 last-resort handler 處理：`WARNING` 以上仍印到 stderr，但不帶時間戳格式；第三方函式庫的 `INFO` 紀錄不再印出。`_isDebug()` 仍為 `False`（有效 level 由 `INFO` 變 `WARNING`）。新增 `liblouis.log` 會在 `<root>/log/` 多一個檔，改變 app 寫入的內容，不屬於本任務。若日後需要，`louis_helper` 已經透過 `braille.louis_helper` 記錄，可直接在那裡掛 handler，不必動膠水。 |
| D3 | `louis_helper` 的修改做在 `scripts/sync-nvda.py` 的 `_adapt_helper()`：(a) `"from logHandler import log\n"` 的替換拿掉 `logging.basicConfig(...)` 區塊，保留 `import logging`、`log = logging.getLogger(__name__)`、`BASE_DIR`、`WINFUNCTYPE`；(b) `"path = brailleTables._tablesDirs.get(registeredTable.source)\n"` 的替換改為 `"path = braille_tables.get_table_directory(registeredTable.source)\n"`。接著把 `vendor/nvda/liblouis/runtime/louis_helper.py` 重寫為 `_adapt_helper(Path("include/nvda/source/louisHelper.py").read_text(encoding="utf-8"))`，UTF-8、`\n` 換行，與 `synchronize()` 寫出的方式完全相同。`vendor/` 中其他都不變（`SOURCE.json` 列出相同檔案與 commit）。被忽略的 `client/braille/louis_helper.py` 不手改；在 Windows 上由 `scripts\install.bat` 更新。 | Helper 是產生檔（見關鍵發現）；手改會在下次 `clean-liblouis`／`install` 時遺失，而 `client/braille/louis_helper.py` 也無法 commit。改寫表是 DotExpress 對 NVDA 檔案的 adapter 層，正是 `storage/refactor.md` 第 7 節第 6 點所要求的。只單獨重新產生 helper，是因為完整 sync 也會還原手改過的 `build/sconscript`（既有偏差）。用同一個函式重新產生，保證快照等於 sync 會為該檔寫出的內容；有測試釘住。 |
| D4 | 保留 `getDefaultTableForCurLang(tableType, lang)` 及其測試。在 docstring 加一行，說明它為了與 NVDA `brailleTables` 對齊而保留，DotExpress 中沒有呼叫者。 | 刪除它會讓 `addTable` 的 `inputForLangs`／`outputForLangs`（由不可修改的 `__tables.py` 傳入）填兩個沒人讀的 dict，並擴大與上游的差異，卻沒有任何執行期好處。把它接上（例如作為某語言的預設表格）會改變使用者拿到的表格，是本任務以外的行為變更。記錄下來，避免之後的 review 重新提起。 |
| D5 | 在 `braille/tables/__init__.py` 的 `getTable`／`listTables` 後面加入 `get_table_directory(source: str) -> str \| None`。內容：`return _tablesDirs.get(source)`，於呼叫時讀模組全域變數。依 roadmap 的命名與 `AGENTS.md` 對新函式的要求使用 snake_case；NVDA 風格的 camelCase 名稱不動。 | 對每個來源的結果都與舊的私有存取相同，包括 `terminate()` 之後（builtin 父 map 仍在）以及之後加入子 map 的情況。`louis_helper` 只需要資料夾，不需要整個 map。 |
| D6 | `MathCATAdapter.close()`：冪等。若有 `_dll_directory_handle` 就關閉並設為 `None`，丟掉 `_libmathcat`，設定 `_closed` 旗標（新的 dataclass 欄位，預設 `False`）。`close()` 之後，`initialize()` 與 `get_braille_for_mathml()` 拋出 `MathCATError("MathCAT adapter is closed")`，且不載入任何東西。`sys.modules["libmathcat_py"]` 不動（擴充模組無法卸載）。 | 讓 runtime 有實際可釋放的東西：以 `os.add_dll_directory` 加入的 DLL 搜尋路徑項目。關閉檢查放在兩個公開方法中（不放在 `_load_libmathcat`），這樣覆寫 `_load_libmathcat` 的既有測試子類別也能測到。關閉後明確失敗，可避免晚到的呼叫者悄悄再次加入 DLL 目錄。 |
| D7 | 刪除 `_SHARED_ADAPTER` 與 `get_shared_mathcat_adapter()`。`mathml_to_nemeth_braille(mathml, braille_code=DEFAULT, *, language, mathcat)` 與 `translate_math_segment(latex, braille_code=DEFAULT, *, language, mathcat)` 以必填 keyword 接收 adapter（任何具有 `get_braille_for_mathml(mathml, braille_code=..., *, language=...)` 的物件；在 `TYPE_CHECKING` 下標註為 `MathCATAdapter`）。`math_service` 在執行期不再 import `conversion.mathcat_adapter`。 | Provider 擁有 adapter 之後，隱藏的單例會成為沒人關閉的第二個擁有者。唯一的正式呼叫者是 provider。`math_service` 仍不涉及原生載入（import 隔離測試照樣通過）。 |
| D8 | `MathCATMathTranslator(*, translate_math, close=None)`。`close()` 在有給 callback 時呼叫它，否則什麼都不做。`translate()` 不變。 | 既有的建構方式（`test_math_translation_adapter.py`、golden 測試）不必修改。`build_translation_runtime` 本來就會把可呼叫的 `close` 變成關閉 callback，所以 provider 的串接不用改。 |
| D9 | `create_default_math_translator(*, platform=None, adapter_factory=None)`。沒給 factory 時使用私有的 `_create_mathcat_adapter()`，回傳 `MathCATAdapter(resource_root=get_default_mathcat_resource_root())`。順序：平台檢查；import（`MathCATMathTranslator`、`translate_math_segment`）；`adapter = adapter_factory()`；`adapter.initialize()`；若 `initialize()` 拋出任何例外，先執行 `adapter.close()` 再讓例外繼續（`ImportError`／`OSError`／`MathCATError` 照舊轉成 `RuntimeUnavailableError`，其他錯誤照舊往外拋）。成功時回傳 `MathCATMathTranslator(translate_math=functools.partial(translate_math_segment, mathcat=adapter), close=adapter.close)`。 | 每個 runtime 一個 adapter，由同一個擁有者建立、初始化與關閉。載入失敗不再讓其 DLL 目錄留在註冊中。錯誤對應與 fallback 記錄不變。測試改用 `adapter_factory`，取代對 `provider.get_shared_mathcat_adapter` 的 patch。 |
| D10 | 關閉順序依 `TranslationRuntime.close()`：callback 以註冊的反序執行，所以先關 MathCAT adapter，再做 liblouis `terminate()`。`OnExit` 與 demo 其他部分不變。 | 兩個 runtime 彼此獨立；這是契約本來就定義的順序。目前數學端沒有 callback。 |
| D11 | 測試 log 隔離：新增測試輔助模組 `client/tests/file_log_isolation.py`，提供一個函式：對指定的 logger 名稱，把每個 logger 的 handler 換成 `logging.NullHandler`、設 `propagate = False`，cleanup 時放回原本完全相同的 handler 與 `propagate`。不論 logger 是否已存在都可用。上述四個模組在模組層級 fixture（`setUpModule`／`tearDownModule`，若模組需要也可用 class fixture）中呼叫它，所以每個模組結束時都還原狀態。不改任何正式模組。 | 只動測試，app 不變。它屬於這裡，因為它是 P2-6 交接指派給 P2-7 的 logging 清理的另一半。替換 handler（而不是 patch `log._log_directory`）之所以可行，是因為 handler 在 import 時就已綁定；它也能承受 `StubScope` 的 eviction：重新 import 的模組再次呼叫 `get_logger`，看到已有 handler 就保留。對 log 呼叫做斷言的測試（`patch.object(dual_view.logger, "debug")`、`RecordingLogger`）照常運作，因為它們替換的是 logger 或其方法，不是 handler。此 commit 獨立，若 reviewer 希望放到別處，可單獨拿掉。 |

## 各檔設計

### `client/braille/tables/__init__.py`（tab、CRLF；逐位元組小心編輯）

- 24-31 行改為 `import logging`、一個空行、`log = logging.getLogger(__name__)`（D1）。前後的空行維持原樣。
- 加入 `get_table_directory`（D5），附簡短 docstring。
- 在 `getDefaultTableForCurLang` 的 docstring 加入 D4 那一行。
- 每一行都保留 `\r\n`。diff 只能出現這些行。檢查：`$PY -c "d=open('client/braille/tables/__init__.py','rb').read(); assert d.count(b'\n')==d.count(b'\r\n')"`。

### `scripts/sync-nvda.py`（4 空白）

只改 `_adapt_helper` 中的兩個替換字串（D3）。marker 檢查與替換迴圈不變，所以未來 NVDA 原始碼若缺少 marker 仍會明確失敗。

### `vendor/nvda/liblouis/runtime/louis_helper.py`（產生檔、tab、LF）

依 D3 重新產生。預期 diff（已在 scratchpad 做出雛形）：五行的 `logging.basicConfig(...)` 區塊（22-26 行）消失，原 65 行（新 60 行）變成 `path = braille_tables.get_table_directory(registeredTable.source)`。其他不變。

### `conversion/mathcat_adapter.py`（tab）

D6 與 D7：加入 `_closed`、`close()`、關閉檢查；刪除單例。`get_default_mathcat_resource_root()` 保留。

### `conversion/math_service.py`（tab）

D7：兩個函式都加上 `mathcat` keyword；`mathml_to_nemeth_braille` 呼叫 `mathcat.get_braille_for_mathml(mathml_text, braille_code=braille_code, language=language)`。`translate_math_segment` 的記錄與 `MathConversionError` 行為不變。

### `adapters/translation/mathcat.py`（4 空白）

D8。

### `adapters/translation/provider.py`（4 空白）

D9。頂層 import 改為 `from conversion.mathcat_adapter import MathCATAdapter, MathCATError, get_default_mathcat_resource_root`（import 時仍不做原生載入）。`create_default_text_translator` 不動。

### 測試（所有動到的測試模組皆為 4 空白）

見測試計畫。

## 遷移（先做特性測試）

每一步都是一個全綠的 commit。確切切分由 plan 決定。

1. **特性測試**（在任何正式程式碼變更之前就是綠的）：
   - 新檔 `client/tests/test_braille_glue.py` 以假的 `braille.liblouis` 載入 `vendor/nvda/liblouis/runtime/louis_helper.py`（如現況所述；結束後還原 `sys.modules`、`braille.liblouis` 屬性，以及 root logger 的 handler 與 level）。它釘住 `_resolveTableInner`：已註冊表格解析到其來源的資料夾（以 patch `braille.tables._tables` 與 `braille.tables._tablesDirs` 驅動，新舊 helper 都會經由它們讀取）、未註冊名稱退回 `TABLES_DIR`（patch 為暫存資料夾）、有 `base` 時從 `dirname(base)` 開始搜尋、找不到的表格拋出列出已搜尋資料夾的 `LookupError`。
   - `tests/test_translation_runtime_provider.py` 新增一個測試，以 `platform="win32"` 包著一個記錄用的假 adapter 建立預設數學 translator，經由一個本地 helper。目前 helper patch `provider.get_shared_mathcat_adapter` 與 `conversion.mathcat_adapter.get_shared_mathcat_adapter`；第 4 步只把 helper 內容改為 `adapter_factory=`。它釘住：任何翻譯前 `initialize()` 恰好一次；`translate("1", braille_code="Nemeth", language="en")` 會呼叫 `get_braille_for_mathml(latex_to_mathml("1"), braille_code="Nemeth", language="en")`，並把假 adapter 的點字格作為單一 token 回傳。
2. **`braille.tables`**（D1、D4、D5）及其新測試。
3. **Helper 改寫**（D3）：`sync-nvda.py`、重新產生的快照、新的 `scripts/tests` 與 client 測試。
4. **MathCAT 注入**（D6-D10）：adapter、math service、translator、provider 及其測試。`tests/test_math_service.py` 與 `tests/test_translation_runtime_provider.py:248-255` 刻意修改（它們 patch 了被刪的單例），改為傳入 `mathcat=`／`adapter_factory=`。
5. **測試 log 隔離**（D11）。

## 測試計畫

約 25 個新測試；確切清單與數量由 plan 決定。除非另註，全都在 Linux 執行。

**特性測試（第 1 步）**：上述四個 resolver 測試與預設數學 translator 串接測試。

**`braille.tables`（第 2 步）**，在 `tests/test_braille_glue.py`：
- 在全新的直譯器中（`subprocess`，如 `test_translation_import_isolation.py`）：`import braille.tables` 之後，`logging.root.handlers == []`、`logging.root.level == logging.WARNING`，且 `braille.tables.log is logging.getLogger("braille.tables")`。第 2 步之前為紅。
- `get_table_directory(TableSource.BUILTIN) == TABLES_DIR`；未知來源回傳 `None`；把 `_tablesDirs` patch 成有子 map 的 chain 時，能找到子 map 中的來源。
- `tests/test_braille_tables_default_lang.py` 維持原樣。

**Helper（第 3 步）**：
- `scripts/tests/test_sync_nvda_liblouis.py`：對 fixture 執行 `synchronize()` 之後，改寫後的 helper 不含 `basicConfig`、含有 `braille_tables.get_table_directory(registeredTable.source)`，且不含 `_tablesDirs`。第 3 步之前為紅。
- 新的 scripts 測試：`_adapt_helper(<repo>/include/nvda/source/louisHelper.py)` 與 `<repo>/vendor/nvda/liblouis/runtime/louis_helper.py` 逐位元組相同。`include/nvda` submodule 未 checkout 時 skip。變更前就成立，變更後讓快照保持誠實。
- `client/tests/test_braille_glue.py`，在全新直譯器中：以假的 `braille.liblouis` 把 vendor helper 載入為 `braille.louis_helper` 後，root logger 沒有 handler、level 為 `WARNING`，`helper.log is logging.getLogger("braille.louis_helper")`，且 `helper._isDebug()` 為 `False`。第 3 步之前為紅。
- 對 vendor helper 與 `braille/tables/__init__.py` 做 AST 檢查：沒有呼叫名為 `basicConfig` 的屬性，helper 沒有存取 `_tablesDirs` 屬性。

**MathCAT（第 4 步）**：
- `tests/test_mathcat_adapter.py`：`close()` 即使呼叫兩次也恰好關閉假 DLL 目錄 handle 一次，並清除 `_libmathcat`；`close()` 之後 `initialize()` 與 `get_braille_for_mathml()` 拋出 `MathCATError`，且不呼叫 `_load_libmathcat`；對從未初始化的 adapter 呼叫 `close()` 不會失敗。
- `tests/test_math_translation_adapter.py`：`close()` 呼叫給定的 callback；沒給時不做事。
- `tests/test_translation_runtime_provider.py`：兩次呼叫 `create_default_math_translator(platform="win32", adapter_factory=...)` 使用兩個不同的 adapter（沒有單例）；以預設 factory（兩者都注入）建立的 runtime 執行 `runtime.close()` 時，MathCAT adapter 恰好關閉一次，且在文字 helper 的 `terminate()` 之前；`initialize()` 拋出 `MathCATError` 的 adapter 會被關閉，呼叫者得到 `RuntimeUnavailableError`；拋出 `ValueError` 的 adapter 會被關閉，且 `ValueError` 往外拋。
- `tests/test_math_service.py`：兩個既有測試改傳假的 `mathcat=`，不再 patch 單例；新增一個測試，確認 `mathml_to_nemeth_braille` 以 `braille_code` 與 `language` 呼叫給定的 adapter。

**Log 隔離（第 5 步）**：輔助函式的測試（handler 與 `propagate` 完全還原；對尚無 handler 的 logger 名稱也可用）；四個模組使用它。驗收標準 6 檢查效果。

## 驗收標準

在所示路徑執行；`$SP`／`$PY` 同上。

1. `cd client && $PY -m unittest discover -s tests`：只有已知的 P2-5 失敗；測試數 = 1071 + 新測試；skip 數不變（9）。
2. `cd client && for s in $(seq 1 20); do $PY $SP/shuffle_harness.py $s; done`：每個 seed 都只回報 P2-5 失敗。
3. 在 repo 根目錄，`$PY -m unittest discover -s scripts/tests`：全部通過（25 + 新增）。
4. 在 repo 根目錄，`$PY $SP/p12/tools/msgid_scan.py client` 回報 `source msgids: 353`，集合相同。
5. 兩個 fixture 的 sha256 不變。
6. App 資料：P2-6 的快照（`$SP/p26impl/snap.sh`：`config.json`／`workspace/` 是否存在、`dictionary/` 下每個檔案的 sha256、`dual_view/` 的非原始碼項目、`log/` 中的檔名）在標準 1-2 前後完全相同，**而且** `client/log/` 中每個檔案的 sha256 前後相同（新增：測試不再追加寫入）。
7. `git diff main --stat -- client/braille/tables/__tables.py vendor/nvda/liblouis/SOURCE.json vendor/nvda/liblouis/build vendor/nvda/liblouis/python vendor/nvda/mathcat` 為空，且被忽略的 `client/braille/liblouis/__init__.py` 與 `client/braille/louis_helper.py` 的 sha256 不變（第 1 步之前先記錄）。
8. `client/braille/tables/__init__.py` 每一行仍為 `\r\n`，且 `git diff main -- client/braille/tables/__init__.py` 只出現 D1、D4、D5 的行。
9. `command grep -rn "basicConfig\|_tablesDirs\.get\|get_shared_mathcat_adapter\|_SHARED_ADAPTER" client scripts vendor --include=*.py --exclude-dir=.venv` 只找到被忽略、尚未重新安裝的 `client/braille/louis_helper.py`（直到 Windows install 更新它為止），以及刻意提到這些名稱的測試文字。
10. `git diff main --stat` 只動到：`client/braille/tables/__init__.py`、`scripts/sync-nvda.py`、`vendor/nvda/liblouis/runtime/louis_helper.py`、`client/conversion/mathcat_adapter.py`、`client/conversion/math_service.py`、`client/adapters/translation/mathcat.py`、`client/adapters/translation/provider.py`、測試計畫中列出的測試模組（加上 `client/tests/file_log_isolation.py` 與 D11 的四個模組）、`scripts/tests/test_sync_nvda_liblouis.py`（或新的 scripts 測試模組），以及 spec 與 plan 檔。

## Windows 待驗證項目（此處無法執行）

- 更新產生的 helper：`scripts\install.bat`（或 `scripts\clean-rebuild-dotexpress.bat`），然後確認 `client\braille\louis_helper.py` 與 `vendor\nvda\liblouis\runtime\louis_helper.py` 相同。
- `cd client && python -m unittest tests.test_liblouis_runtime tests.test_translation_runtime_provider tests.test_mathcat_adapter -v`（roadmap 的指令加上 adapter 測試）。`test_table_resolver_finds_bundled_table` 與 `test_chinese_default_table_translates` 會經過 `get_table_directory`。
- 原始碼執行（在主控台中 `python gui.py`）：app 啟動，轉換一份含中文、英文與數學的文件，結束時沒有 traceback；主控台不再出現 root logger 帶時間戳的 `INFO` 行（預期如此，D2）。
- 打包版：轉換同一份文件，將 BRL 輸出與 `main` 的建置比對（逐位元組相同），結束，並確認 `log\translation.log` 沒有新的 fallback 警告、`log\math.log` 沒有新的錯誤。
- 在數學轉換進行中結束：不會當掉（MathCAT adapter 現在會先關閉；見風險）。

## 風險

- **Windows checkout 上過時的產生 helper。** 在執行 `scripts\install.bat` 之前，`client\braille\louis_helper.py` 仍是舊版：仍呼叫 `basicConfig` 並讀取 `_tablesDirs`。這仍可運作，因為 `_tablesDirs` 保留（它仍是 `get_table_directory` 背後的儲存）。新 helper 需要新的 `braille.tables`；兩者都在此分支落地，`braille.tables` 先。
- **打包。** PyInstaller 從工作目錄收集 `client/braille/louis_helper.py`，所以沒重新安裝就打包，會帶著舊 helper。相同的緩解：打包前先 install（`clean-rebuild-dotexpress.bat` 兩者都做）。
- **原始碼執行時主控台輸出改變**（D2）。只影響開發者主控台；已記錄。
- **轉換進行中關閉 MathCAT。** 若 `OnExit` 執行時有 worker thread 正在 MathCAT 裡，已關閉的 adapter 會讓該片段以 `MathConversionError` 失敗（記到 `math.log`），而不是完成。liblouis `terminate()` 已存在同樣的競態，本任務也不改變 `OnExit` 執行的時機。此處無法檢查；列入 Windows 待驗證項目。
- **關閉時移除 DLL 目錄。** 此時 `libmathcat_py.pyd` 及其相依都已載入，移除搜尋路徑項目不會卸載它們。只能在 Windows 上確認。
- **Resolver 回歸。** 正式環境傳完整表格路徑，所以被改的那一行只對裸表格名稱執行。Linux 測試以假 liblouis 直接驅動產生 helper 的 resolver；Windows runtime 測試涵蓋真正的 DLL。
- **測試 process 中的 root logger 狀態。** 第 1 步的 resolver 測試會載入呼叫 `basicConfig` 的舊 helper；它們會還原 root logger 的 handler 與 level。紅／綠的 root 檢查在 subprocess 中執行，避免先前的測試掩蓋結果。

## 範圍外／後續事項

- 完整執行 `sync-nvda.py` 會還原手改過的 `vendor/nvda/liblouis/build/sconscript`（`9aa8355`、`1bd19d7`）。修法：把這些修改移進 `_adapt_sconscript`，或記錄 sconscript 已不再同步。
- `louis_helper._resolveTable` 呼叫不帶訊息的 `log.exception()`（NVDA 的 logger 接受，標準函式庫的會拋 `TypeError`）。只在表格無法解析時才有影響；callback 不論如何都回傳 `NULL`。在另一個任務中於 `_adapt_helper` 修正（例如 `log.exception("Could not resolve braille tables")`）。
- `__tables.py` 的 `localedir` 指向不存在的 `client/braille/locales`（P0 M-5，P2-3 顯示沒有可見影響）。不變。
- 透過 `log.get_logger` 提供選用的 `liblouis.log` 檔（D2）：屬產品決策。
