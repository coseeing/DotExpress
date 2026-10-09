# liblouis 測試探測（W-1）設計

## 目標

任務 W-1 讓真實 liblouis 的測試能在 Windows 上執行。有三個測試模組以直接 import `braille.liblouis` 的方式檢查 liblouis 綁定是否可用。在 Windows 11 上，這個 import 會載入錯誤的 DLL、失敗，而且錯誤的 DLL 會在整個行程剩下的時間裡一直保持載入。結果是 Windows 驗證清單第 4 項（`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md:258`）從未真正跑到真實 liblouis 的測試：以名稱執行時指令直接以錯誤結束，在 `discover` 底下這些測試被跳過或出錯，卻看不出原因。

本任務完成後：

- 測試模組只透過 `braille.louis_helper` 取得綁定，與正式程式碼走同一條路徑。兩個模組層級的探測改為 import helper（無法載入時仍然 raise `unittest.SkipTest`），`LiblouisRuntimeTests.setUpClass` 改用 `louis_helper.louis`。
- 一個守衛測試：只要 `client/tests/` 底下有任何模組直接 import `braille.liblouis` 就失敗。

只改測試。正式程式碼、產生檔、vendored 檔案、使用者可見字串、msgid（353）與 fixture 都不變。

## 現況（2026-10-09 於 Windows 11、`main` `d0ae3b4` 驗證）

`$PY` 是 `client\.venv\Scripts\python.exe`（Python 3.13，含 wxPython）。內建的 `client/braille/liblouis.dll`（3.37.0）與其 tables 由 `scripts\build-liblouis.bat` 建置、`scripts\install.bat` 安裝。

### 兩個 DLL

- Windows 11 內建一個 Microsoft 簽章的 `C:\Windows\System32\liblouis.dll`（朗讀程式的點字功能使用）。它的 ABI 較舊，沒有匯出 `lou_freeTableFile` 與 `lou_freeTableInfo`。
- 產生的綁定 `client/braille/liblouis/__init__.py`（git-ignored，由 `scripts\install.bat` 產生）以裸檔名載入 DLL：`liblouis = _loader["liblouis.dll"]`（Windows 上是 `windll`），接著在第 271 行設定 `liblouis.lou_freeTableFile.restype`。
- `client/braille/louis_helper.py`（git-ignored，產生檔）在 `os.add_dll_directory(BASE_DIR)` 之內 import 綁定（第 25-31 行：`with dll_directory: from braille import liblouis as louis`），因此裸檔名會解析到內建的 DLL。它以 `louis_helper.louis` 公開這個模組。
- 正式程式碼中唯一 import helper 的地方是 `adapters/translation/provider.py:73`（`from braille import louis_helper`）。沒有任何正式模組直接 import `braille.liblouis`（對 `client/` grep，排除 `.venv`、`tests` 與產生檔）。

### 失敗方式

裸的 `from braille import liblouis`（沒有加入 DLL 目錄）會載入 System32 的 DLL，並 raise `AttributeError: function 'lou_freeTableFile' not found`。Windows 會讓那個 DLL 保持載入；同一個行程之後每次以裸檔名載入 `liblouis.dll`，包括 helper 在 `add_dll_directory` 之內的那次，都會拿到已載入的模組。整個行程因此被污染：

```text
$PY -c "exec('try:\n from braille import liblouis\nexcept AttributeError as e:\n print(e)'); from braille import louis_helper"
-> function 'lou_freeTableFile' not found，接著 louis_helper 的 import 拋出 AttributeError
$PY -c "from braille import louis_helper; from braille import liblouis; print(liblouis.version())"
-> 3.37.0
```

### 三個探測

| 模組 | 縮排 | 探測 |
| --- | --- | --- |
| `client/tests/test_translation_language_result.py` | tabs | 模組層級：`try: from braille import liblouis` / `except Exception: raise unittest.SkipTest(...)` |
| `client/tests/test_language_detection_translation.py` | tabs | 同上 |
| `client/tests/test_liblouis_runtime.py` | 4 spaces | `setUpClass`：先 `from braille import liblouis` 再 `from braille import louis_helper`；`cls.louis = liblouis` |

基線（於 `client/`，`PYTHONIOENCODING=utf-8`）：

- 清單第 4 項 `$PY -m unittest tests.test_liblouis_runtime tests.test_translation_language_result tests.test_language_detection_translation -v`：一個測試都沒跑。以名稱載入時不會攔截模組層級的 `SkipTest`，所以指令以 traceback `unittest.case.SkipTest: liblouis bindings unavailable: function 'lou_freeTableFile' not found` 結束。
- `$PY -m unittest discover -s tests`：`Ran 1136 tests`，`FAILED (failures=6, errors=2, skipped=7)`。其中兩個 skip 是模組探測（`liblouis bindings unavailable: function 'lou_freeTableFile' not found`），一個 error 是 `setUpClass (test_liblouis_runtime.LiblouisRuntimeTests)`。其餘的 failure 與另一個 error 與 liblouis 無關（見 plan 的結果段）。

### 測試中其他提到 `braille.liblouis` 的地方（都不是 import）

- `tests/test_braille_glue.py` 把一個假模組放進 `sys.modules["braille.liblouis"]` 並設為 `braille.liblouis` 屬性，從未 import 真正的綁定。一段 subprocess 程式碼（第 165 行）只 import `tests.test_braille_glue`。
- `tests/test_translation_result_core.py:37` 在 subprocess 程式碼裡有字串 `"braille.liblouis"`，用來斷言這個模組**沒有**被 import。
- `tests/test_liblouis_adapter.py` 與 `tests/test_translation_golden.py` import 的是 `adapters.translation.liblouis`，另一個模組。

## 決策

- **D1. 測試走正式程式碼的載入路徑。** 修改產生的綁定（以完整路徑載入）或 helper 可以從根本為所有人修好，但兩者都是產生檔（`scripts/sync-nvda.py`、`scripts\install.bat`），不在範圍內。正式程式碼因為經過 helper，本來就安全。只有測試繞過了 helper，所以要改的是測試。
- **D2. 模組層級的探測改為 import `braille.louis_helper`，並以 `except Exception` 保留 `SkipTest` 後備。** 在 Linux 上（沒有 `WINFUNCTYPE`）前面既有的檢查仍會先跳過；在沒有產生 helper 的 checkout 上，import 會 raise `ModuleNotFoundError`，模組仍然跳過。訊息維持 `liblouis bindings unavailable: {exc}`。兩個模組其餘部分不變：它們本來就透過會 import helper 的 `adapters.translation.provider` 翻譯。
- **D3. `LiblouisRuntimeTests.setUpClass` 只 import helper**，並設定 `cls.louis = louis_helper.louis`。測試方法照舊使用 `self.louis` 與 `self.helper`。
- **D4. 守衛是對 `client/tests/*.py`（測試套件是扁平的）import 敘述的 AST 掃描。** 它回報：`braille.liblouis`（或其子模組）的 `ast.Import`、從 `braille` 匯入 `liblouis` 的 `ast.ImportFrom`、從 `braille.liblouis`（或其子模組）匯入的 `ast.ImportFrom`，以及第一個引數為字串 `"braille.liblouis"` 的 `importlib.import_module`／`__import__` 呼叫。它不解析字串字面值：上面的 subprocess 程式碼只是提到這個名稱，目前也沒有任何一段 import 綁定（grep）。寫入 `sys.modules`（`test_braille_glue.py` 的假模組）不是 import，不會被標記。
- **D5. 守衛放在哪裡。** `client/tests/test_braille_glue.py`，放在 `GlueSourceTest` 旁邊（該模組已經以 AST 檢查膠水原始碼、import 了 `ast` 並定義 `CLIENT_DIR`；4 spaces）。它在所有平台上都會執行。一個小的偵測器測試釘住每一種會被標記的寫法，以及不會被標記的相似寫法（`from braille import louis_helper`、`from adapters.translation.liblouis import ...`、`sys.modules["braille.liblouis"] = fake`），讓守衛不會因為什麼都沒比對到而通過。

## 測試計畫

新增於 `client/tests/test_braille_glue.py`，class `LiblouisImportGuardTest`：

1. `test_detector_flags_every_direct_import_form`：在記憶體中解析程式碼片段；偵測器對會被標記的寫法回傳其行號，對相似寫法回傳空。
2. `test_test_modules_load_liblouis_only_through_louis_helper`：掃描每個 `client/tests/*.py`，預期 `[]`。修正前為紅燈，恰好列出三個探測（`test_language_detection_translation.py:9`、`test_liblouis_runtime.py:19`、`test_translation_language_result.py:10`）。

修改：兩個探測與 `setUpClass`（D2、D3）。在有內建 DLL 的 Windows 上，三個模組接著會執行它們的 7 個真實測試（5 + 1 + 1）；在 Linux 上仍然跳過。

## 遷移步驟

1. 紅燈：加入 `LiblouisImportGuardTest`；測試 2 失敗並列出三個探測，測試 1 通過。
2. 綠燈：修改三個探測。守衛與修正放在同一個 commit。

## 驗收標準

1. `LiblouisImportGuardTest` 通過；修正前它以三個探測失敗。
2. 清單第 4 項在 Windows 上執行時不再出現模組層級的 `SkipTest` traceback，也沒有 `setUpClass` 錯誤；若有測試因其他原因（真實 liblouis 的行為）失敗，記錄下來，不在此修正。
3. Windows 上的 `discover` 不再回報兩個 `liblouis bindings unavailable` 跳過與 `setUpClass` 錯誤；三個模組以外沒有新的失敗。
4. 只有 `client/tests/test_braille_glue.py`、`client/tests/test_liblouis_runtime.py`、`client/tests/test_translation_language_result.py`、`client/tests/test_language_detection_translation.py` 與 W-1 文件改變。兩份 fixture 的 sha256 不變（`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`）。

## 風險

- 若同一個行程中有在這三個模組之前執行、且未經 helper 就 import `braille.liblouis` 的測試，仍會污染它們。守衛涵蓋測試模組；正式程式碼目前沒有這種 import（D1）。
- 探測修好後，真實 liblouis 的測試第一次在 Windows 上執行；它們揭露的失敗是真實行為，會回報而不是掩蓋。

## 範圍外／後續事項

- 讓產生的綁定本身安全（以套件旁的絕對路徑載入 `liblouis.dll`，或在載入的 DLL 缺少符號時以清楚的訊息失敗）。這屬於產生器（`scripts/sync-nvda.py`／`scripts\install.bat`），能保護未來任何直接 import 的程式碼。
- 把守衛擴大到正式模組。
