# Platform Translation Adapters Review Task 1

日期：2026-07-06

## 審閱依據

- `docs/superpowers/finish_task.md`
- `docs/superpowers/specs/2026-07-06-platform-translation-adapters-design.md`
- `docs/superpowers/plans/2026-07-06-platform-translation-adapters.md`
- Superpowers code review 原則：先驗證 finding，再修正 Critical／Important 問題，修正後由 main agent 重新審閱。

## Commit 審閱順序

依 commit 時間由舊到新審閱：

1. `5bd69d9` `refactor: isolate translation result model`
   - `TranslationResult` 已與 liblouis import 分離。
   - 平台中立核心測試保留 addition、empty mapping 與 import isolation。
   - 結論：通過。
2. `d3bbbb3` `feat: add character translation fallback`
   - 文字與數學 fallback 均符合逐字元映射規格。
   - 空白、換行、`raw`、atomic replacement 與 position arrays 行為正確。
   - 結論：通過。
3. `885a18d` `refactor: wrap liblouis translation adapter`
   - table path、mode、一般 mapping 與 single-token mapping 保留既有 native 行為。
   - 結論：通過。
4. `41cc0a7` `refactor: wrap MathCAT translation adapter`
   - eager initialization 與單一 math token mapping 符合設計。
   - translation-time failure 未被靜默轉為 fallback。
   - 結論：通過。
5. `915d663` `feat: select translation runtimes independently`
   - 四種 text/math native/fallback 組合與 idempotent close 已覆蓋。
   - 第一輪發現 Important finding，詳見下節。
6. `b0d79a8` `refactor: inject translation runtime into conversion`
   - runtime 已顯式傳入 conversion entry points，service 未建立 provider 或 singleton。
   - 第一輪發現一項整合層 Important finding，詳見下節。
7. `db54bff` `refactor: assemble translation runtime in app`
   - `BrailleApp` 負責建立與關閉 runtime，`BrailleFrame` 負責向 conversion 傳遞。
   - GUI 不再直接持有 liblouis lifecycle。
   - 結論：通過。
8. `db97b76` `test: cover cross-platform translation alignment`
   - clean-process import isolation 與 fallback dual-view mapping 已覆蓋。
   - 結論：通過。

## 第一輪 Findings

### Important 1：liblouis 載入失敗未進入 fallback

位置：`client/adapters/translation/provider.py`

`louis_helper.initialize()` 原本位於 `ImportError`／`OSError` 正規化範圍之外。若 Windows 上缺少 DLL 或 dependent DLL，初始化可能直接拋出 `OSError`，使應用程式啟動失敗，而不是只將 text capability 切換為 fallback。這違反 design 對 capability-unavailable 的定義。

修正：

- 將 native adapter import、`braille.louis_helper` import 與 `initialize()` 納入已知載入錯誤的正規化範圍。
- MathCAT native adapter import 同樣納入一致的 error boundary。
- 新增 `ImportError`、`OSError` regression tests。
- 保留 `ValueError` 等 unexpected defects 原樣傳播。

### Important 2：開發入口仍使用已刪除 API

位置：`client/main.py`

該腳本仍匯入已由 `5bd69d9` 刪除的 `translate()`，並以舊 signature 呼叫 `translate_and_wrap_both()`，因此無法 import 或執行。

修正：

- 改用 `build_default_translation_runtime()` 與 `conversion.service` entry point。
- 傳入完整 conversion paths、tables 與 explicit runtime。
- 使用 `try/finally` 關閉 runtime。
- 加入 `if __name__ == "__main__"`，避免 import 時執行 demo。
- 新增 import smoke test。

## 修正與重審

修正由獨立 sub-agent 執行，採 RED/GREEN 流程；工具未提供指定 sub-agent 模型版本的參數，因此無法驗證模型是否為 GPT-5.4。

sub-agent RED：

- provider 新增測試在修正前出現 3 個 errors。
- `main` import 在修正前因 native DLL import 失敗。

sub-agent GREEN：

```bash
cd client
python3 -m unittest tests.test_translation_runtime_provider tests.test_main tests.test_conversion_service -v
git diff --check
python3 main.py
```

結果：35 tests 通過、diff check 通過，demo 可在目前平台使用 fallback 完成。

main agent 第二輪重新檢查修正 diff、error boundary、runtime lifecycle 與 import side effect，未發現新的 Critical、Important 或 Minor finding。

## 最終驗證

```bash
cd client
python3 -m unittest \
  tests.test_translation_result_core \
  tests.test_translation_fallback \
  tests.test_liblouis_adapter \
  tests.test_math_translation_adapter \
  tests.test_translation_runtime_provider \
  tests.test_mathcat_adapter \
  tests.test_math_service \
  tests.test_conversion_service \
  tests.test_dual_view_model \
  tests.test_dual_view_frame \
  tests.test_font_support \
  tests.test_gui_document_flows \
  tests.test_translation_import_isolation \
  tests.test_main \
  -v
python3 -m py_compile \
  adapters/translation/provider.py \
  main.py \
  tests/test_translation_runtime_provider.py \
  tests/test_main.py
git diff --check
```

結果：102 tests 通過，py_compile 與 diff check 通過。

完整 client discovery 另執行：

```bash
cd client
python3 -m unittest discover -s tests -v
```

結果：287 tests 中 12 個 errors、7 個 skipped。Errors 集中於既有 importer／測試環境依賴，包括缺少 `mammoth`、不完整的 `lxml`／EPUB／`PdfReader` 測試替身，未落在本次 translation adapter commits 的變更範圍。

Windows native liblouis／MathCAT regression tests 無法在目前 Linux 環境執行，仍需在 Windows build environment 驗證。

## 最終結論

修正後實作符合 design 與 plan。main agent 第二輪 review 無未解決 findings；目前剩餘風險僅為尚未在 Windows 實機執行 native runtime regression tests。
