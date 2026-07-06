# Platform Translation Adapters 完成說明

參考文件：

- `docs/superpowers/specs/2026-07-06-platform-translation-adapters-design.md`
- `docs/superpowers/plans/2026-07-06-platform-translation-adapters.md`

## 完成內容

- 將 `client/translate.py` 精簡為平台中立的 `TranslationResult` 模型。
- 新增 `client/adapters/translation/`：
  - `contracts.py`
  - `fallback.py`
  - `liblouis.py`
  - `mathcat.py`
  - `provider.py`
- 以 `TranslationRuntime` 注入 `client/conversion/service.py`，讓文字與數學翻譯能力可獨立選擇 native 或 fallback。
- 將 runtime 的建立與關閉移到 `client/gui.py` 的 `BrailleApp` 生命週期。
- 新增跨平台 import isolation、fallback alignment、runtime provider、native adapter 等測試。

## 驗證結果

已通過：

- `python3 -m unittest tests.test_translation_result_core tests.test_translation_fallback tests.test_liblouis_adapter tests.test_math_translation_adapter tests.test_translation_runtime_provider tests.test_mathcat_adapter tests.test_math_service tests.test_conversion_service tests.test_dual_view_model tests.test_dual_view_frame tests.test_font_support tests.test_gui_document_flows tests.test_translation_import_isolation -v`
- `python3 -m unittest tests.test_gui_document_flows tests.test_client_init -v`
- `python3 -m unittest tests.test_conversion_service -v`
- `python3 -m unittest tests.test_translation_import_isolation tests.test_dual_view_model tests.test_font_support tests.test_dual_view_frame -v`
- `git diff --check`

未通過：

- `python3 -m unittest discover -s tests -v`

失敗項目集中在既有匯入器/測試環境依賴，與本次 translation adapter 變更不重疊，包含：

- `mammoth` 未安裝，導致 `test_dialog_validation` / `test_docx_importer` 相關失敗
- `lxml` / `PdfReader` 測試替身或環境能力不足，導致 `test_html_to_ast`、`test_epub_importer`、`test_import_fixtures` 的 importer 類測試失敗

## 變更檔案重點

- `client/adapters/translation/*`
- `client/conversion/service.py`
- `client/conversion/mathcat_adapter.py`
- `client/gui.py`
- `client/translate.py`
- `client/tests/test_translation_result_core.py`
- `client/tests/test_translation_fallback.py`
- `client/tests/test_liblouis_adapter.py`
- `client/tests/test_math_translation_adapter.py`
- `client/tests/test_translation_runtime_provider.py`
- `client/tests/test_conversion_service.py`
- `client/tests/test_gui_document_flows.py`
- `client/tests/test_dual_view_model.py`
- `client/tests/test_translation_import_isolation.py`

## 此次新增 commit list

- `5bd69d9` `refactor: isolate translation result model`
- `d3bbbb3` `feat: add character translation fallback`
- `885a18d` `refactor: wrap liblouis translation adapter`
- `41cc0a7` `refactor: wrap MathCAT translation adapter`
- `915d663` `feat: select translation runtimes independently`
- `b0d79a8` `refactor: inject translation runtime into conversion`
- `db54bff` `refactor: assemble translation runtime in app`
- `db97b76` `test: cover cross-platform translation alignment`
