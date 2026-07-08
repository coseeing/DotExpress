# Refactor 3 Next Phase 完成說明

參考文件：

- `docs/superpowers/specs/2026-07-08-refactor3-next-phase-design.md`
- `docs/superpowers/plans/2026-07-08-refactor3-next-phase.md`

## 完成內容

- 讓 `DocumentController` 成為 document state 的單一來源，補上 `document_names`、`open_document_name`、`selected_document_name`、`get_document()`、`sort_documents()` 等 accessor / mutation helper。
- 將 `BrailleFrame` 的 document state 改成 controller-backed delegation，移除 `_sync_document_controller_state()` 的雙向同步路徑。
- 將 conversion completion policy 移入 per-job state，讓 `ConversionJobRequest` / `ConversionJobSuccess` / `ConversionJobFailure` 都攜帶 `ConversionCompletionPolicy`。
- 更新 GUI conversion 流程，讓 manual convert、single export、batch export 各自使用自己的 completion policy，不再依賴 frame-global mutable flags。
- 新增 `client/documents/formats.py`，集中管理 document format descriptor、import/export capability、wildcard、loader、writer 與 `requires_braille` 規則。
- 讓 `workspace.py` 與 `ui/import_dialog.py` 改為讀取共享 registry，不再各自 hardcode format knowledge。
- 補齊 controller、format registry、workspace、import dialog、conversion jobs、GUI flow 的回歸測試。

## 驗證結果

已通過：

- `python3 -m unittest tests.test_document_controller tests.test_document_formats tests.test_document_workspace tests.test_import_dialog tests.test_conversion_jobs tests.test_gui_document_flows -v`
- `python3 -m unittest tests.test_document_session tests.test_conversion_service -v`
- `git diff --check`

## 此次新增 commit list

- `df01017` `refactor: converge document and conversion boundaries`
