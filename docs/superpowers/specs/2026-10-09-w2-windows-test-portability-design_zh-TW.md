# Windows 測試可攜性（W-2）設計

## 目標

任務 W-2 消除 `python -m unittest discover -s tests` 在 Windows 11 上回報的六個測試失敗。這些失敗只是因為測試寫死了 POSIX 的行為（其中一個則是寫錯大小寫）。每一項的正式程式碼行為都與重構前（基準 `6e5819f`）完全相同，錯的只是預期值。本任務完成後，每個預期值都寫成在 Windows 與 POSIX 上皆成立，Linux CI 仍會通過。

只改測試。正式程式碼、產生檔、vendored 檔案、使用者可見字串、msgid 與 fixture 都不變。

## 現況（2026-10-09 於 Windows 11、`main` `9a4ae81` 驗證）

`$PY` 是 `client\.venv\Scripts\python.exe`（Python 3.13）。在 `client/` 下設定 `PYTHONIOENCODING=utf-8`，`discover -s tests` 回報 `Ran 1143`、`FAILED (failures=7, errors=1, skipped=5)`（W-1 結果）。其中六個失敗屬於本任務範圍：

| # | 測試 | Windows 上的實際值 | 測試的預期值 |
| --- | --- | --- | --- |
| 1 | `test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_real_writers_produce_today_bytes` | `alpha.html` 位元組使用 `\r\n` | `\n` |
| 2 | `test_gui_document_flows.DocumentMenuAndExportCharacterizationTest.test_dual_view_and_html_export_render_math_with_real_mathml` | 同上 | `\n` |
| 3 | `test_dual_view_browser.DualViewBrowserTest.test_chromium_commands_request_new_window_and_size` | `C:\Chrome\chrome.exe` | `C:/Chrome/chrome.exe` |
| 4 | `test_dual_view_browser.DualViewBrowserTest.test_firefox_command_requests_new_window_and_size` | `C:\Firefox\firefox.exe` | `C:/Firefox/firefox.exe` |
| 5 | `test_liblouis_adapter.LiblouisTextTranslatorTest.test_regular_translation_preserves_native_mapping` | `/tables\en.ctb` | `/tables/en.ctb` |
| 6 | `test_liblouis_runtime.LiblouisRuntimeTests.test_built_wrapper_loads_bundled_dll` | `Could not determine expected liblouis version` | `configure.ac` 中的版本 |

### 基準證據（正式程式碼自 `6e5819f` 起未變）

- **1、2。** `documents/formats.py` 的 `_write_html` 現在（第 108 行）與 `6e5819f`（第 93 行）都以 `Path.write_text(html, encoding="utf-8")` 寫檔。`write_text` 以文字模式、`newline=None` 開檔，所以每個 `\n` 都會變成 `os.linesep`。在 Windows 上從 `git archive` 取出的 `6e5819f` 副本執行該 writer，寫出的檔案只有 CRLF（沒有單獨的 LF）。測試拿來比較的是 `render_dual_view_html(...).encode("utf-8")`，其中是 `\n`。這兩個測試都是在 `6e5819f` 之後加入的；只適用 POSIX 的是它們的預期值，而不是 writer。
- **3、4。** `dual_view/browser.py` 的 `build_browser_command` 與 `6e5819f` 逐位元組相同，回傳 `str(executable)`。在 Windows 上 `str(Path("C:/Chrome/chrome.exe"))` 是 `C:\Chrome\chrome.exe`，正是 `subprocess.Popen` 預期的原生格式。`6e5819f` 版本的 `tests/test_dual_view_browser.py` 在 Windows 上同樣這兩個測試失敗。
- **5。** `adapters/translation/liblouis.py` 與 `6e5819f` 相同，以 `os.path.join(self._tables_dir, table)` 組合路徑。`6e5819f` 版本的 `tests/test_liblouis_adapter.py` 在 Windows 上以相同方式失敗。這裡的 helper 是假的；真正的 liblouis 在 Windows 上兩種分隔符號都接受。
- **6。** 測試以 `AC_INIT\(\[liblouis\]` 讀取 `include/liblouis/configure.ac`（區分大小寫；`6e5819f` 時的 regex 相同）。兩個 commit 的 submodule 都是 `2aa5f84b`（`v3.37.0`），內容為 `AC_INIT([Liblouis], [3.37.0], ...)`；大寫 `L` 來自 liblouis commit `84b1a81e`。內建 DLL 回報 `3.37.0`。不涉及任何正式程式碼；在 W-1 之前這個測試從未在 Windows 上執行過。

## 決策

- **D1. 預期值跟隨平台，而非寫死常數。** 每項修正都用正式程式碼所依賴的同一條標準函式庫規則推導預期值，因此在兩個平台上都通過，且仍然鎖定精確的值：
  - 1、2：模組 helper `text_file_bytes(text)` 回傳 `text.replace("\n", os.linesep).encode("utf-8")`，即 `write_text(text, encoding="utf-8")` 產生的位元組。用於 `alpha.html`、`beta.html` 與數學匯出。在 POSIX 上 `os.linesep == "\n"`，預期值不變。
  - 3、4：預期 `str(Path("C:/Chrome/chrome.exe"))`（Edge 與 Firefox 同理）。在 POSIX 上是 `C:/Chrome/chrome.exe`，不變。
  - 5：預期 `os.path.join("/tables", "en.ctb")`。在 POSIX 上是 `/tables/en.ctb`，不變。
  - 6：在 `AC_INIT` 搜尋加上 `re.IGNORECASE`。這個類別只在 Windows 上執行（`skipUnless win32`），但 regex 與平台無關。
- **D2. 不改正式程式碼。** 以 `newline="\n"` 寫 HTML、正規化執行檔路徑、或以 `/` 組合 table 路徑，都會改變現在 Windows 上的行為；這不在範圍內也沒有必要（沒有人回報這是缺陷）。
- **D3. 每個原因一個 commit**（HTML 換行、瀏覽器路徑、table 路徑組合、configure.ac 大小寫），每個只動一個測試檔。

## 驗收條件

1. 六個測試在 Windows 上個別執行都通過。
2. Windows 上 `discover -s tests`：`Ran 1143`、`FAILED (failures=1, errors=1, skipped=5)`。剩下的失敗與錯誤是範圍外的 `test_conversion_service...test_translate_with_language_does_not_duplicate_existing_spaces_around_math`（P2-5 決策）與 `test_dictionary_name_prompt...test_case_only_rename_still_renames`（不分大小寫檔案系統上的已知缺陷）；跳過的是五個平台相關的 skip。
3. 只有 `client/tests/test_gui_document_flows.py`、`client/tests/test_dual_view_browser.py`、`client/tests/test_liblouis_adapter.py`、`client/tests/test_liblouis_runtime.py` 與 W-2 文件變動。兩個 fixture 的 sha256 不變（`translation_golden.json` `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`、`dictionary_entries_trace.json` `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`）。

## 範圍外

- P2-5 空白案例與只改大小寫的詞典重新命名缺陷（見上）。
- 決定匯出的 HTML 是否應在所有平台都使用 LF。
